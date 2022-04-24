from abc import ABC
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    # Meta
    Internal = "Internal"
    Protocol = "Protocol"
    Scheduler = "Scheduler"
    Meta = "Meta"

    ExceptionNotHandled = "ExceptionNotHandled"
    ApiNotSuccessful = "ApiNotSuccessful"

    # Bot
    BotOnline = "BotOnline"
    BotOffline = "BotOffline"

    # Message
    GroupMessage = "GroupMessage"
    FriendMessage = "FriendMessage"
    TempMessage = "TempMessage"

    # Event
    GroupRecall = "GroupRecall"
    FriendRecall = "FriendRecall"

    GroupPermissionChange = "GroupPermissionChange"

    GroupFileUpload = "GroupFileUpload"

    GroupMute = "GroupMute"
    GroupUnmute = "GroupUnmute"

    GroupJoin = "GroupJoin"
    GroupLeave = "GroupLeave"

    GroupJoinRequest = "GroupJoinRequest"
    GroupInvitedRequest = "BotInvitedJoinGroupRequest"

    FriendAdd = "FriendAdd"
    FriendRemove = "FriendRemove"

    FriendAddRequest = "FriendAddRequest"

    Unknown = "Unknown"


MessageEventTypes = [
    EventType.FriendMessage,
    EventType.GroupMessage,
    EventType.TempMessage,
]


@dataclass
class Event(ABC):
    type: EventType


class EventProvider(ABC):
    pass
