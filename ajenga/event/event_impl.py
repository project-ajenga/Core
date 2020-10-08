from abc import ABC
from dataclasses import dataclass
from dataclasses import field

from ajenga.event.event import Event
from ajenga.event.event import EventType
from ajenga.message import MessageChain
from ajenga.message import MessageIdType
from ajenga.message import Message_T
from ajenga.models import ContactIdType
from ajenga.models import GroupPermission


class MethodNotInjectedError(RuntimeError):
    pass


@dataclass
class Sender:
    qq: ContactIdType
    name: str
    permission: GroupPermission = field(default=GroupPermission.NONE)


@dataclass
class MessageEvent(Event, ABC):
    message: MessageChain
    message_id: MessageIdType
    sender: Sender

    async def reply(self, message: Message_T, **kwargs):
        raise MethodNotInjectedError


@dataclass
class GroupMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.GroupMessage, init=False)
    group: ContactIdType


@dataclass
class FriendMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.FriendMessage, init=False)


@dataclass
class TempMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.TempMessage, init=False)
    group: ContactIdType


@dataclass
class GroupRecallEvent(Event):
    type: EventType = field(default=EventType.GroupRecall, init=False)
    qq: ContactIdType
    message_id: MessageIdType
    operator: ContactIdType
    group: ContactIdType


@dataclass
class FriendRecallEvent(Event):
    type: EventType = field(default=EventType.FriendRecall, init=False)
    qq: ContactIdType
    message_id: MessageIdType


@dataclass
class GroupMuteEvent(Event):
    type: EventType = field(default=EventType.GroupMute, init=False)
    qq: ContactIdType
    operator: ContactIdType
    group: ContactIdType
    duration: int


@dataclass
class GroupUnmuteEvent(Event):
    type: EventType = field(default=EventType.GroupUnmute, init=False)
    qq: ContactIdType
    operator: ContactIdType
    group: ContactIdType


@dataclass
class GroupJoinEvent(Event):
    type: EventType = field(default=EventType.GroupJoin, init=False)
    qq: ContactIdType
    operator: ContactIdType
    group: ContactIdType


@dataclass
class GroupLeaveEvent(Event):
    type: EventType = field(default=EventType.GroupLeave, init=False)
    qq: ContactIdType
    operator: ContactIdType
    group: ContactIdType


@dataclass
class RequestEvent(Event, ABC):
    async def accept(self, **kwargs):
        raise NotImplementedError

    async def reject(self, **kwargs):
        raise NotImplementedError

    async def ignore(self):
        raise NotImplementedError


@dataclass
class NewFriendRequestEvent(RequestEvent, ABC):
    type: EventType = field(default=EventType.NewFriendRequest, init=False)
    qq: ContactIdType
    comment: str


@dataclass
class GroupJoinRequestEvent(RequestEvent, ABC):
    type: EventType = field(default=EventType.GroupJoinRequest, init=False)
    qq: ContactIdType
    group: ContactIdType
    comment: str


@dataclass
class GroupInvitedRequestEvent(RequestEvent, ABC):
    type: EventType = field(default=EventType.GroupInvitedRequest, init=False)
    operator: ContactIdType
    group: ContactIdType
    comment: str
