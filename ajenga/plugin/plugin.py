import importlib
import inspect
import json
import os
import sys
from types import ModuleType
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union

import ajenga
from ajenga.event import MetaEvent
from ajenga.event import MetaEventType
from ajenga.log import Logger
from ajenga.log import logger
from ajenga.provider import meta_provider
from . import Service
from . import remove_service
from . import set_current_plugin


class Plugin:
    name: str
    author: Union[str, List[str]]
    version: str
    usage: str

    module: Optional[ModuleType]
    path: str
    services: Dict[str, Service]

    logger: Logger

    def __init__(self,
                 info: Dict,
                 path: str = ''):
        self.name = info['name']
        self.author = info['author']
        self.version = info['version']
        self.usage = info['usage']
        self.module = None
        self.path = path
        self.services = {}
        self.logger = ajenga.log.get_logger(self.name)
        self.loaded = False

    def load(self,
             module: ModuleType):
        self.module = module
        self.path = module.__name__
        self.loaded = True

    def add_service(self, service):
        self.services[service.name] = service
        logger.info(f'Succeeded to load Service "{service.key}" ')


_loaded_plugins: Dict[str, Plugin] = {}


def add_plugin(plugin: Plugin, force: bool = False) -> None:
    """Register a Plugin

    :param plugin: Plugin object
    :param force: Ignore existed
    :return:
    """
    if not force and plugin.path in _loaded_plugins:
        logger.warning(f"Plugin {plugin} already exists")
        return

    if plugin.name:
        _loaded_plugins[plugin.name] = plugin
    if plugin.path:
        _loaded_plugins[plugin.path] = plugin


def remove_plugin(key: Union[str, Plugin]) -> bool:
    """Remove a Plugin

    :param key: Plugin object or module path or name
    :return: Success or not
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        logger.warning(f"Plugin {key} not exists")
        return False

    if plugin.name in _loaded_plugins:
        del _loaded_plugins[plugin.name]
    if plugin.path in _loaded_plugins:
        del _loaded_plugins[plugin.path]
    return True


def get_plugin(key: str) -> Optional[Plugin]:
    """Get Plugin object by Plugin module path or name

    :param key: Plugin module path or name
    :return: Plugin object
    """
    return _loaded_plugins.get(key, None)


async def load_plugin(*, module_path: str = None, plugin_dir: str = None) -> Optional[Plugin]:
    """Load a Plugin by Plugin module path or Plugin directory

    :param module_path:
    :param plugin_dir:
    :return:
    """
    if not plugin_dir:
        if not module_path:
            raise ValueError()
        elif module_path.startswith('.'):
            plugin_dir = '.' + module_path.replace('.', '/')
        else:
            plugin_dir = './' + module_path.replace('.', '/')
    else:
        if plugin_dir.startswith('.'):
            module_path = plugin_dir.replace('/', '.')[1:]
        else:
            module_path = plugin_dir.replace('/', '.')

    logger.info(f'Loading Plugin {module_path} from {plugin_dir} ...')

    try:
        plugin_info_path = os.path.join(os.path.expanduser(plugin_dir), ajenga.config.PLUGIN_INFO_FILE)
        with open(plugin_info_path, encoding='utf-8') as f:
            plugin_info = json.load(f)

        if plugin_info.get('name') and get_plugin(plugin_info['name']):
            logger.error(f'Plugin {plugin_info["name"]} already exists')
            return None
        plugin = Plugin(plugin_info, path=module_path)
        set_current_plugin(plugin)
        add_plugin(plugin)
    except Exception as e:
        logger.exception(e)
        logger.error(f'Failed to load Plugin config from {plugin_dir}')
        return None

    try:
        module = importlib.import_module(module_path)
        plugin.load(module)
        add_plugin(plugin, True)
    except Exception as e:
        logger.exception(e)
        logger.error(f'Failed to load Plugin module from {module_path}')
        await unload_plugin(plugin, True)
        return None

    for service in plugin.services.values():
        await meta_provider.send(MetaEvent(MetaEventType.ServiceLoaded, service=service))

    logger.info(f'Succeeded to load Plugin "{plugin.name}"')

    await meta_provider.send(MetaEvent(MetaEventType.PluginLoaded, plugin=plugin))

    return plugin


async def unload_plugin(key: Union[str, Plugin], forced: bool = False) -> bool:
    """Unload a Plugin

    :param key: Plugin object or module path or name
    :param forced: Forced to unload
    :return: Success or not
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        logger.warning(f"Plugin {key} not exists")
        return False

    plugin_name = plugin.name

    await meta_provider.send(MetaEvent(MetaEventType.PluginUnload, plugin=plugin))

    for service in plugin.services.values():
        try:
            await meta_provider.send(MetaEvent(MetaEventType.ServiceUnload, service=service))
            remove_service(service)
        except Exception as e:
            logger.exception(e)
            logger.error(f'Failed to unload service "{service}", error: {e}')

    result = remove_plugin(plugin)
    if not result and not forced:
        return False

    if plugin.path:
        for module in list(filter(lambda x: x.startswith(plugin.path), sys.modules.keys())):
            del sys.modules[module]

    logger.info(f'Succeeded to unload Plugin "{plugin_name}"')
    return True


async def reload_plugin(key: Union[str, Plugin]) -> Optional[Plugin]:
    """Reload a Plugin

    :param key: Plugin object or module path or name
    :return: Success or not
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        logger.warning(f"Plugin {key} not exists")
        return None

    module_path = plugin.path
    return await load_plugin(module_path=module_path) if await unload_plugin(plugin) else None


def get_loaded_plugins() -> Set[Plugin]:
    """Get all plugins loaded.

    :return: a set of Plugin objects
    """
    return set(_loaded_plugins.values())


def caller_name(skip):
    def stack_(frame):
        frame_list = []
        while frame:
            frame_list.append(frame)
            frame = frame.f_back
        return frame_list

    stack = stack_(sys._getframe(1))
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parent_frame = stack[start]

    module = inspect.getmodule(parent_frame)

    return module


def get_current_plugin(*, depth=1) -> Optional[Plugin]:
    module_name = caller_name(depth).__name__
    while not get_plugin(module_name) and '.' in module_name:
        module_name, _ = module_name.rsplit('.', maxsplit=1)

    return get_plugin(module_name)
