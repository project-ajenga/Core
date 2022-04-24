from dataclasses import dataclass, field
from enum import Enum

from ajenga.event import Event, EventProvider, EventType
from ajenga.router.keystore import KeyStore


class MetaEventType(Enum):
    PluginLoad = "PluginLoad"
    PluginLoaded = "PluginLoaded"
    PluginUnload = "PluginUnload"
    PluginUnloaded = "PluginUnloaded"


@dataclass(init=False)
class MetaEvent(Event):
    type: EventType = field(default=EventType.Meta, init=False)
    _dict: dict = field(default_factory=dict, init=False)

    def __init__(self, meta_type, **kwargs):
        self.type = EventType.Meta
        self._dict = {}
        self._dict.update({'meta_type': meta_type, **kwargs})

    def __getattr__(self, item):
        return self._dict[item]


class ExceptionNotHandledEvent(Event):
    type: EventType = field(default=EventType.ExceptionNotHandled, init=False)
    event: Event
    source: EventProvider
    exception: Exception
    store: KeyStore
