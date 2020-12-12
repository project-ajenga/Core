import re
from functools import partial
from ajenga.typing import AsyncIterable
from ajenga.typing import Pattern
from ajenga.typing import Type
from ajenga.typing import TypeVar
from ajenga.typing import Union
from ajenga.typing import final

from ajenga import routing as std
from ajenga.event import EventType
from ajenga.event import FriendMessageEvent
from ajenga.event import GroupMessageEvent
from ajenga.event import MessageEvent
from ajenga.event import MessageEventTypes
from ajenga.event import TempMessageEvent
from ajenga.message import MessageElement
from ajenga.message import MessageType
from ajenga.routing.models import NonterminalNode
from ajenga.routing.models import TerminalNode
from ajenga.routing.keyfunc import KeyFunctionImpl
from ajenga.routing.keystore import KeyStore
from ajenga.routing.std import AbsNonterminalNode
from ajenga.routing.std import EqualNode
from ajenga.routing.std import make_graph_deco
from . import event_type_is
from .trie import PrefixNode

key_message_content_string = KeyFunctionImpl(lambda event: event.message.as_plain())
key_message_content_string_stripped = KeyFunctionImpl(lambda event: event.message.as_plain().strip())
key_message_content_string_lstripped = KeyFunctionImpl(lambda event: event.message.as_plain().lstrip())

key_message_content_string_reversed = KeyFunctionImpl(
    lambda event: event.message.as_plain()[::-1])
key_message_content_string_reversed_stripped = KeyFunctionImpl(
    lambda event: event.message.as_plain()[::-1].strip())
key_message_content_string_reversed_lstripped = KeyFunctionImpl(
    lambda event: event.message.as_plain()[::-1].lstrip())

key_message_qq = KeyFunctionImpl(lambda event: event.sender.qq)
key_message_group = KeyFunctionImpl(lambda event: event.group)
key_message_permission = KeyFunctionImpl(lambda event: event.sender.permission)

is_message = event_type_is(*MessageEventTypes)
is_friend = event_type_is(EventType.FriendMessage)
is_group = event_type_is(EventType.GroupMessage)
is_temp = event_type_is(EventType.TempMessage)
is_private = is_friend | is_temp

qq_from = partial(make_graph_deco(EqualNode), key=key_message_qq)
group_from = partial(make_graph_deco(EqualNode), key=key_message_group)

permission_is = partial(make_graph_deco(EqualNode), key=key_message_permission)


def equals(text: str, *texts: str, strip: bool = True):
    if strip:
        return make_graph_deco(EqualNode)(text, *texts, key=key_message_content_string_stripped)
    else:
        return make_graph_deco(EqualNode)(text, *texts, key=key_message_content_string)


def startswith(text: str, *texts: str, strip: bool = True):
    if strip:
        return make_graph_deco(PrefixNode)(text, *texts, key=key_message_content_string_lstripped)
    else:
        return make_graph_deco(PrefixNode)(text, *texts, key=key_message_content_string)


def endswith(text: str, *texts: str, strip: bool = True):
    if strip:
        return make_graph_deco(PrefixNode)(
            text[::-1],
            *map(lambda x: x[::-1], texts),
            key=key_message_content_string_reversed_lstripped)
    else:
        return make_graph_deco(PrefixNode)(
            text[::-1],
            *map(lambda x: x[::-1], texts),
            key=key_message_content_string_reversed)


def match(pattern: Pattern):
    return std.if_(KeyFunctionImpl(
        lambda event: re.match(pattern, event.message.as_plain()),
        key='match',
    ))


M = TypeVar('M', bound=MessageElement)


@final
class MessageTypeNode(AbsNonterminalNode):
    def __init__(self,
                 msg_type: Union[Type[MessageElement], MessageType] = ...,
                 *or_more: Union[Type[MessageElement], MessageType]):
        super().__init__()
        if msg_type is not ...:
            msg_type = msg_type.type if not isinstance(msg_type, MessageType) else msg_type
            self.add_key(msg_type)
        for more in or_more:
            more = more.type if not isinstance(more, MessageType) else more
            self.add_key(more)

    async def route(self, args, store: KeyStore) -> AsyncIterable[TerminalNode]:
        nodes = set()
        message = store['event'].message
        for msg in message:
            if msg.type in self._successors:
                nodes.update(self._successors[msg.type])

        for node in nodes:
            if isinstance(node, TerminalNode):
                yield node
            elif isinstance(node, NonterminalNode):
                async for terminal in node.route(args, store):
                    yield terminal


def has(msg_type: Type[MessageElement], *or_more: Type[MessageElement]):
    return make_graph_deco(MessageTypeNode)(msg_type, *or_more)


def same_event_as(ev: MessageEvent):
    if isinstance(ev, GroupMessageEvent):
        return is_group & group_from(ev.group) & qq_from(ev.sender.qq)
    elif isinstance(ev, FriendMessageEvent):
        return is_friend & qq_from(ev.sender.qq)
    elif isinstance(ev, TempMessageEvent):
        return is_temp & qq_from(ev.sender.qq)
    else:
        raise TypeError
