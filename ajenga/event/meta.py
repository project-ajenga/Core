from enum import Enum

from ajenga.event import Event
from ajenga.event import EventType


class MetaEventType(Enum):
    ServiceLoaded = "ServiceLoaded"
    ServiceUnload = "ServiceUnload"

    PluginLoaded = "PluginLoaded"
    PluginUnload = "PluginUnload"


class MetaEvent(Event):
    type: EventType = EventType.Meta

    def __init__(self, meta_type, **kwargs):
        super().__init__(meta_type=meta_type, **kwargs)