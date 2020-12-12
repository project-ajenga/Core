import asyncio
import json
import os
from datetime import datetime
from functools import wraps
from ajenga.typing import Any
from ajenga.typing import Callable
from ajenga.typing import Dict
from ajenga.typing import Optional
from ajenga.typing import Set
from ajenga.typing import Union
from ajenga.typing import final

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler as Scheduler

import ajenga
import ajenga.router as router
from ajenga.event import Event
from ajenga.event import EventType
from ajenga.event import FriendMessageEvent
from ajenga.event import GroupMessageEvent
from ajenga.event import GroupPermission
from ajenga.event import MessageEvent
from ajenga.event import MessageEventTypes
from ajenga.event import MetaEventType
from ajenga.event import TempMessageEvent
from ajenga.log import Logger
from ajenga.log import logger
from ajenga.message import Message_T
from ajenga.models import ContactIdType
from ajenga.protocol import Api
from ajenga import app
from ajenga.routing import std
from ajenga.routing.models import Graph
from ajenga.routing.models import TerminalNode
from ajenga.routing.keyfunc import PredicateFunction
from ajenga.routing.std import PredicateNode

_loaded_services: Dict[str, "Service"] = {}
_tmp_current_plugin: Optional["Plugin"] = None

_service_config_dir = os.path.expanduser('./service_config/')
os.makedirs(_service_config_dir, exist_ok=True)

# block list
_black_list_group = {}  # Dict[group, expr_time]
_black_list_user = {}  # Dict[qq, expr_time]


def _load_service_config(service_key):
    config_file = os.path.join(_service_config_dir, f'{service_key}.json')
    if not os.path.exists(config_file):
        return {}  # config file not found, return default config.
    try:
        with open(config_file, encoding='utf8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.exception(e)
        return {}


def _save_service_config(service):
    config_file = os.path.join(_service_config_dir, f'{service.key}.json')
    with open(config_file, 'w', encoding='utf8') as f:
        json.dump({
            "name": service.name,
            "use_priv": service.use_priv,
            "manage_priv": service.manage_priv,
            "enable_on_default": service.enable_on_default,
            "visible": service.visible,
            "enable_group": list(service.enable_group),
            "disable_group": list(service.disable_group),
            'user_privs': list(service.user_privs.items())
        }, f, ensure_ascii=False, indent=2)


class Privilege:
    EVERYBODY = -1000
    BLACK = -999
    DEFAULT = 0
    PRIVATE = 20
    GROUP = 20
    PRIVATE_OTHER = 30
    PRIVATE_DISCUSS = 40
    PRIVATE_GROUP = 50
    PRIVATE_FRIEND = 60
    ADMIN = 100
    OWNER = 150
    WHITE = 200
    SUPERUSER = 990
    TERMINAL = 995
    NOBODY = 1000


@final
class ServiceGraphImpl(Graph):
    """Graph implementation supports __call__ as decorator

    """
    sv: "Service"

    def __init__(self, sv, **kwargs):
        super().__init__(**kwargs)
        self.sv = sv

    def __call__(self, func) -> TerminalNode:
        if self.closed:
            raise ValueError("Cannot call on a closed graph!")
        if not isinstance(func, TerminalNode):
            func = app.engine.handler_cls(func)
        g = self.apply(func)
        self.sv._terminals.add(func)
        app.engine.subscribe(g)
        return func

    def copy(self):
        return ServiceGraphImpl(sv=self.sv, start=self.start.copy(), closed=self.closed)


class Service:
    name: str
    plugin: "Plugin"
    logger: Logger

    def __init__(self,
                 name=None,
                 *,
                 use_priv=Privilege.DEFAULT,
                 manage_priv=Privilege.ADMIN,
                 enable_on_default=None,
                 visible=None,
                 ):
        self.name = name or 'base'
        self.plugin = _tmp_current_plugin
        self.logger = self.plugin.logger.getChild(self.name)

        config = _load_service_config(self.key)

        self.use_priv = config.get('use_priv', use_priv)
        self.manage_priv = config.get('manage_priv', manage_priv)
        self.enable_on_default = config.get('enable_on_default')
        if self.enable_on_default is None:
            if enable_on_default is None:
                self.enable_on_default = name is None
            else:
                self.enable_on_default = enable_on_default
        self.visible = config.get('visible')
        if self.visible is None:
            if visible is None:
                self.visible = name is not None
            else:
                self.visible = visible
        self.enable_group = set(config.get('enable_group', []))
        self.disable_group = set(config.get('disable_group', []))
        self.user_privs = dict(config.get('user_privs', []))

        # self._node_key = PredicateFunction(lambda event: self.check_priv(event), notation=self)
        # self._node = PredicateNode(self._node_key)
        self._sv_node = router.meta_service_is(self)
        self._terminals: Set[TerminalNode] = set()

        self._scheduler = Scheduler()

        @self.on_loaded()
        def _start_scheduler():
            if self._scheduler and not self._scheduler.running and self._scheduler.get_jobs():
                self._scheduler.configure(ajenga.config.APSCHEDULER_CONFIG)
                self._scheduler.start()

        @self.on_unload()
        def _on_unload():
            self.logger.info(f'Unloading... Unsubscribe all {len(self._terminals)} subscribers.')
            app.engine.unsubscribe_terminals(self._terminals)

            # Stop scheduler
            if self._scheduler and self._scheduler.running:
                self._scheduler.remove_all_jobs()

        # Add to service list
        if self.key in _loaded_services:
            self.logger.warning(f"Service {self} already exists")
        _loaded_services[self.key] = self
        self.plugin.add_service(self)

    def check_priv(self, event: Event, required_priv: Union[int, Callable[[int], bool]] = None):
        if event.type in MessageEventTypes:
            required_priv = self.use_priv if required_priv is None else required_priv
            user_priv = self.get_user_priv(event)

            if isinstance(event, GroupMessageEvent):
                if not self.check_enabled(event.group):
                    return False
            if isinstance(required_priv, int):
                return bool(user_priv >= required_priv)
            elif isinstance(required_priv, Callable):
                return required_priv(user_priv)
            else:
                return False
        else:
            return True

    @property
    def key(self):
        if self.plugin is None:
            self.logger.error('Access key when service initializing!')
        else:
            return f'{self.plugin.name}.{self.name}'

    def __str__(self):
        return f'<Service: {self.key}>'

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    def on(self, graph=std.true, *, priv: Union[int, Callable[[int], bool]] = None):
        return ServiceGraphImpl(self) & graph & PredicateNode(
            PredicateFunction(lambda event: self.check_priv(event, required_priv=priv), notation=self))

    def on_message(self, graph=std.true, *, priv: Union[int, Callable[[int], bool]] = None):
        return self.on(ajenga.router.message.is_message & graph, priv=priv)

    def on_loaded(self, arg: Any = None):
        g = (ServiceGraphImpl(self) &
             router.event_type_is(EventType.Meta) &
             router.meta_type_is(MetaEventType.ServiceLoaded) &
             self._sv_node
             )
        if isinstance(arg, Callable):
            return g(arg)
        else:
            return g

    def on_unload(self, arg: Any = None):
        g = (ServiceGraphImpl(self) &
             router.event_type_is(EventType.Meta) &
             router.meta_type_is(MetaEventType.ServiceUnload) &
             self._sv_node
             )
        if isinstance(arg, Callable):
            return g(arg)
        else:
            return g

    @staticmethod
    def check_block_group(group: int):
        if group in _black_list_group and datetime.now() > _black_list_group[group]:
            del _black_list_group[group]  # 拉黑时间过期
            return False
        return bool(group in _black_list_group)

    @staticmethod
    def check_block_user(qq: int):
        if qq in _black_list_user and datetime.now() > _black_list_user[qq]:
            del _black_list_user[qq]  # 拉黑时间过期
            return False
        return bool(qq in _black_list_user)

    @staticmethod
    def get_priv_from_event(event: Event):
        if isinstance(event, GroupMessageEvent):
            if event.sender.qq in ajenga.config.SUPERUSERS:
                return Privilege.SUPERUSER
            elif Service.check_block_user(event.sender.qq):
                return Privilege.BLACK
            elif event.sender.permission == GroupPermission.OWNER:
                return Privilege.OWNER
            elif event.sender.permission == GroupPermission.ADMIN:
                return Privilege.ADMIN
            elif event.sender.permission:
                return Privilege.GROUP
        elif isinstance(event, FriendMessageEvent):
            if event.sender.qq in ajenga.config.SUPERUSERS:
                return Privilege.SUPERUSER
            elif Service.check_block_user(event.sender.qq):
                return Privilege.BLACK
            else:
                return Privilege.PRIVATE_FRIEND
        elif isinstance(event, TempMessageEvent):
            if event.sender.qq in ajenga.config.SUPERUSERS:
                return Privilege.SUPERUSER
            elif Service.check_block_user(event.sender.qq):
                return Privilege.BLACK
            else:
                return Privilege.PRIVATE_GROUP
        return Privilege.DEFAULT

    async def get_user_priv_in_group(self, qq: ContactIdType, event: GroupMessageEvent, api: Api):
        priv = self.get_user_priv(qq)
        if priv == Privilege.BLACK:
            return priv
        member_info = await api.get_group_member_info(
            group=event.group,
            qq=qq)
        if member_info.ok:
            if member_info.data.permission == GroupPermission.OWNER:
                return max(priv, Privilege.OWNER)
            elif member_info.data.permission == GroupPermission.ADMIN:
                return max(priv, Privilege.ADMIN)
            else:
                return max(priv, Privilege.GROUP)

    def get_user_priv(self, qq_or_event: Union[ContactIdType, MessageEvent]) -> int:
        if isinstance(qq_or_event, ContactIdType):
            if qq_or_event in ajenga.config.SUPERUSERS:
                return Privilege.SUPERUSER
            else:
                return self.user_privs.get(qq_or_event, Privilege.DEFAULT)
        elif isinstance(qq_or_event, MessageEvent):
            qq = qq_or_event.sender.qq
            ev_priv = self.get_priv_from_event(qq_or_event)
            sv_priv = self.user_privs.get(qq, Privilege.DEFAULT)
            if qq in ajenga.config.SUPERUSERS:
                return Privilege.SUPERUSER
            elif ev_priv == Privilege.BLACK or sv_priv == Privilege.BLACK:
                return Privilege.BLACK
            else:
                return max(ev_priv, sv_priv)
        else:
            self.logger.error(f'Unknown qq_or_event {qq_or_event}')
            return Privilege.DEFAULT

    def set_user_priv(self, qq_or_event: Union[ContactIdType, MessageEvent], priv: int):
        # print(self.user_privs)
        if isinstance(qq_or_event, int):
            self.user_privs[qq_or_event] = priv
        elif isinstance(qq_or_event, MessageEvent):
            self.user_privs[qq_or_event.sender.qq] = priv
        else:
            self.logger.error(f'Unknown qq_or_event {qq_or_event}')
        _save_service_config(self)

    def set_enable(self, group: ContactIdType):
        self.enable_group.add(group)
        self.disable_group.discard(group)
        _save_service_config(self)
        self.logger.info(f'Service {self.name} is enabled at group {group}')

    def set_disable(self, group: ContactIdType):
        self.enable_group.discard(group)
        self.disable_group.add(group)
        _save_service_config(self)
        self.logger.info(f'Service {self.name} is disabled at group {group}')

    def check_enabled(self, group: ContactIdType):
        return bool((group in self.enable_group) or (self.enable_on_default and group not in self.disable_group))

    async def get_enabled_groups(self) -> dict:
        ret = {}
        for qq, ses in app.get_sessions().items():
            group_list = await ses.api.get_group_list()
            for group in group_list.data:
                if self.check_enabled(group.id):
                    ret[group.id] = qq
        return ret

    def scheduled_job(self, *args, **kwargs) -> Callable:
        kwargs.setdefault('timezone', pytz.timezone('Asia/Shanghai'))
        kwargs.setdefault('misfire_grace_time', 60)
        kwargs.setdefault('coalesce', True)

        def deco(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper():
                try:
                    self.logger.info(f'Scheduled job {func.__name__} started.')
                    await func()
                except Exception as e:
                    self.logger.exception(e)
                    self.logger.error(f'{type(e)} occurred when doing scheduled job {func.__name__}.')

            return self.scheduler.scheduled_job(*args, **kwargs)(wrapper)

        return deco

    async def broadcast(self, *messages: Message_T, interval=0.2):
        groups = await self.get_enabled_groups()
        for group, qq in groups.items():
            try:
                for message in messages:
                    await app.get_session(qq).api.send_group_message(group=group, message=message)
                    await asyncio.sleep(interval)
            except Exception as e:
                self.logger.exception(e)
                self.logger.error(f"Failed to broadcast to group {group}")


def set_current_plugin(plugin: "Plugin") -> None:
    """Set current plugin so the loading service can get its plugin

    :param plugin: Plugin
    :return:
    """
    global _tmp_current_plugin
    _tmp_current_plugin = plugin


def get_service(key: str) -> Optional[Service]:
    """Get service object by key

    :param key: Service key
    :return: Service object
    """
    return _loaded_services.get(key, None)


def remove_service(key: Union[str, Service]) -> bool:
    """Remove a service by service object or key
    This function only remove service from global list

    :param key: Service object or key
    :return: Success or not
    """
    service = get_service(key) if isinstance(key, str) else key
    if not service:
        logger.warning(f"Service {key} not exists")
        return False

    del _loaded_services[service.key]
    return True


def get_loaded_services() -> Set[Service]:
    return set(_loaded_services.values())
