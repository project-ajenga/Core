import os
from typing import Optional

import ajenga
from ajenga.log import logger
from . import Plugin
from . import Service
from . import get_current_plugin
from . import get_plugin


class DirectoryType:
    MODULE = 0
    DATA = 1
    RESOURCE = 2
    TEMP = 3


def get_plugin_dir(pl, dtype: int) -> Optional[str]:
    if isinstance(pl, Service):
        plugin = pl.plugin
    elif isinstance(pl, Plugin):
        plugin = pl
    elif not pl:
        plugin = get_current_plugin(depth=2)
    else:
        plugin = get_plugin(pl)
    if not plugin:
        logger.error(f'Failed to get dir: plugin {pl} not found')
        return None

    if dtype == DirectoryType.MODULE:
        return os.path.dirname(plugin.module.__file__)
    elif dtype == DirectoryType.RESOURCE:
        directory = os.path.expanduser(ajenga.config.RESOURCE_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    elif dtype == DirectoryType.DATA:
        directory = os.path.expanduser(ajenga.config.DATA_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    elif dtype == DirectoryType.TEMP:
        directory = os.path.expanduser(ajenga.config.TEMP_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    else:
        logger.error(f'Failed to get {dtype} dir for plugin {plugin}')
        return None


def ensure_file_path(pl, dtype, path, *paths, as_abs: bool = False, as_url: bool = False) -> Optional[str]:
    if not pl:
        pl = get_current_plugin(depth=2)
    root_path = get_plugin_dir(pl, dtype)
    file_path = os.path.join(root_path, path, *paths)
    file_path = os.path.normpath(file_path)
    dir_path = os.path.dirname(file_path)
    if os.path.normcase(file_path).startswith(os.path.normcase(root_path)):
        os.makedirs(dir_path, exist_ok=True)
        if as_url:
            return f'file:///{os.path.abspath(file_path)}'
        elif as_abs:
            return os.path.abspath(file_path)
        else:
            return file_path
    else:
        logger.error(f'Could not access outside plugin files! {pl} {file_path}')
        return None
