from functools import partial

from ajenga.event import EventType
from ajenga.router.keyfunc import KeyFunctionImpl
from ajenga.router.std import EqualNode, make_graph_deco
from ajenga.router.trie import PrefixNode

key_event_type = KeyFunctionImpl(lambda event: event.type)
key_meta_type = KeyFunctionImpl(lambda event: event.meta_type)
key_meta_plugin = KeyFunctionImpl(lambda event: event.plugin)
key_channel = KeyFunctionImpl(lambda event: event.channel)
key_protocol = KeyFunctionImpl(lambda event: event.protocol)


def key_(__key):
    return KeyFunctionImpl(lambda event: getattr(event, __key))


event_type_is = partial(make_graph_deco(EqualNode), key=key_event_type)
meta_type_is = partial(make_graph_deco(EqualNode), key=key_meta_type)
meta_plugin_is = partial(make_graph_deco(EqualNode), key=key_meta_plugin)
channel_is = partial(make_graph_deco(EqualNode), key=key_channel)
protocol_is = partial(make_graph_deco(EqualNode), key=key_protocol)


def channel(channel: str):
    return event_type_is(EventType.Custom) & channel_is(channel)


def protocol(protocol: str):
    return event_type_is(EventType.Protocol) & protocol_is(protocol)


from . import message
from .message import is_message
