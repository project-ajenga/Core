from ajenga.typing import Any, Container, Dict

PLUGIN_INFO_FILE: str = 'plugin.json'

PLUGIN_MODULE_PREFIX: str = 'plugins'
PLUGIN_DIR: str = './plugins'
RESOURCE_DIR: str = './res'
DATA_DIR: str = './data'
TEMP_DIR: str = './temp'

LOG_DIR: str = './logs'

APSCHEDULER_CONFIG: Dict[str, Any] = {'apscheduler.timezone': 'Asia/Shanghai'}

SUPERUSERS: Container[int] = []

ENABLE_INSERT_ZWSP: bool = True
