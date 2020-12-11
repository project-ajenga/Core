import asyncio
import time
from dataclasses import dataclass
from typing import List
from typing import Tuple

from ajenga import app
from ajenga import router
from ajenga.event import Event
from ajenga.event import EventProvider
from ajenga.event import EventType
from ajenga.message import MessageIdType
from ajenga.message import Quote
from ajenga.provider import BotSession
from ajenga.routing import std
from ajenga.routing.keystore import KeyStore
from ajenga.routing.models import Graph
from ajenga.routing.models import Priority
from ajenga.routing.models import Task
from ajenga.routing.models import TerminalNode
from ajenga.routing.models.execution import _executor_context
from ajenga.routing.models.execution import _task_context

_CANDIDATES_KEY = '_wakeup_candidates'
_SUSPEND_OTHER_KEY = 'suspend_other'
_SUSPEND_NEXT_PRIORITY_KEY = 'suspend_next_priority'


class SchedulerSource(EventProvider):
    pass


_scheduler_source = SchedulerSource()


@dataclass
class SchedulerEvent(Event):
    type: EventType = EventType.Unknown


class _ContextWrapperMeta(type):

    def __getattr__(self, item):
        return _task_context.get().args[1][item]

    def __setattr__(self, key, value):
        _task_context.get().args[1][key] = value

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __setitem__(self, key, value):
        self.__setattr__(key, value)


class _ContextWrapper(metaclass=_ContextWrapperMeta):
    @classmethod
    async def wait_until(cls,
                         graph: Graph,
                         *,
                         timeout: float = 3600,
                         suspend_other: bool = False,
                         suspend_next_priority: bool = False,
                         ):

        task = _task_context.get()
        task.state[_SUSPEND_OTHER_KEY] = suspend_other
        task.state[_SUSPEND_NEXT_PRIORITY_KEY] = suspend_next_priority

        async def _check_timeout():
            cur_time = time.time()
            if cur_time - task.last_active_time > timeout:
                task.raise_(TimeoutError())
                app.engine.unsubscribe_terminals([_dumpy_node])
                return False
            return True

        async def _add_candidate(_store: KeyStore):
            if _CANDIDATES_KEY not in _store:
                _store[_CANDIDATES_KEY] = []
            _store[_CANDIDATES_KEY].append((task, _dumpy_node))

        @app.on(std.if_(_check_timeout) &
                graph &
                std.process(_add_candidate))
        @std.handler(priority=Priority.Never)
        async def _dumpy_node():
            pass

        async def _set_timeout():
            await asyncio.sleep(timeout)
            await app.handle_event(_scheduler_source, SchedulerEvent())

        asyncio.create_task(_set_timeout())

        await task.pause()

    @classmethod
    async def wait_next(cls,
                        graph: Graph = std.true,
                        *,
                        timeout: float = 3600,
                        suspend_other: bool = False,
                        suspend_next_priority: bool = False,
                        ):
        return await cls.wait_until(router.message.same_event_as(this.event) & graph,
                                    timeout=timeout,
                                    suspend_other=suspend_other,
                                    suspend_next_priority=suspend_next_priority
                                    )

    @classmethod
    async def wait_quote(cls,
                         message_id: MessageIdType = ...,
                         bot: BotSession = ...,
                         graph: Graph = std.true,
                         *,
                         timeout: float = 3600,
                         suspend_other: bool = False,
                         suspend_next_priority: bool = False,
                         ):
        message_id = this.event.message_id if message_id is ... else message_id
        bot = this.bot if bot is ... else bot
        return await cls.wait_until(router.message.has(Quote)
                                    & std.if_(lambda event, source:
                                              event.message.get_first(Quote).id == message_id and source == bot)
                                    & graph,
                                    timeout=timeout,
                                    suspend_other=suspend_other,
                                    suspend_next_priority=suspend_next_priority
                                    )

    @classmethod
    def suspend_next_priority(cls):
        _executor_context.get().next_priority = False


@app.on(std.true)
@std.handler(priority=Priority.Wakeup)
async def _check_wait(_store: KeyStore):
    def _wakeup(candi, node):
        candi.priority = _task_context.get().priority
        _executor_context.get().add_task(candi)
        app.engine.unsubscribe_terminals([node])

    candidates: List[Tuple[Task, TerminalNode]] = _store.get(_CANDIDATES_KEY, [])
    candidates.sort(key=lambda e: e[0].last_active_time)

    _suspend_other = False
    _suspend_next_priority = False

    while not _suspend_other and candidates:
        candidate, dumpy_node = candidates.pop()
        _suspend_other = candidate.state[_SUSPEND_OTHER_KEY]
        _suspend_next_priority |= candidate.state[_SUSPEND_NEXT_PRIORITY_KEY]
        _wakeup(candidate, dumpy_node)

    if _suspend_next_priority:
        _executor_context.get().next_priority = False


class TimeoutError(Exception):
    pass


this = _ContextWrapper
