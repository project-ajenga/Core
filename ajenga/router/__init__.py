from functools import partial

from ajenga.router.trie import PrefixNode
from ajenga.router.keyfunc import KeyFunctionImpl
from ajenga.router.std import EqualNode
from ajenga.router.std import make_graph_deco

key_event_type = KeyFunctionImpl(lambda event: event.type)
key_meta_type = KeyFunctionImpl(lambda event: event.meta_type)
key_meta_service = KeyFunctionImpl(lambda event: event.service)

event_type_is = partial(make_graph_deco(EqualNode), key=key_event_type)
meta_type_is = partial(make_graph_deco(EqualNode), key=key_meta_type)
meta_service_is = partial(make_graph_deco(EqualNode), key=key_meta_service)

from . import message
from .message import is_message
