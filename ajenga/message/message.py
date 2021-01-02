import copy
import hashlib
from abc import ABC
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from ajenga.typing import Iterable
from ajenga.typing import List
from ajenga.typing import Optional
from ajenga.typing import Tuple
from ajenga.typing import Type
from ajenga.typing import TypeVar
from ajenga.typing import TYPE_CHECKING
from ajenga.typing import Union

from ajenga.models import ContactIdType


if TYPE_CHECKING:
    from ajenga.app import BotSession


RefererIdType = Optional[int]
MessageIdType = int
ImageIdType = str
VoiceIdType = str


class MessageType(Enum):
    Meta = "Meta"
    Plain = "Plain"
    At = "At"
    AtAll = "AtAll"
    Face = "Face"
    Image = "Image"
    Quote = "Quote"

    Voice = "Voice"
    App = "App"
    Json = "Json"
    Xml = "Xml"

    Forward = "Forward"

    # Not fully supported yet
    # FlashImage = "FlashImage"
    # Poke = "Poke"

    Unknown = "Unknown"


@dataclass
class MessageElement(ABC):
    type: MessageType
    referer: RefererIdType = field(default=None, init=False)

    def copy(self):
        return copy.deepcopy(self)

    async def raw(self) -> "Optional[MessageElement]":
        """Convert bot dependent message into universal raw message

        :return:
        """
        self.referer = None
        return self

    async def to(self, bot: "Optional[BotSession]", **kwargs) -> "Optional[MessageElement]":
        """Convert universal message into bot dependent message

        :return:
        """
        if bot is None:
            return await self.raw()

        return await bot.wrap_message(self, **kwargs)

    def as_plain(self) -> str:
        return ''

    def as_display(self) -> str:
        return ''


M = TypeVar('M', bound=MessageElement)


class MessageChain(List[MessageElement]):
    def __init__(self, msgs: Union[str, MessageElement, Iterable[MessageElement]] = ...):
        super().__init__()
        if msgs is ...:
            pass
        elif isinstance(msgs, str):
            self.append(Plain(text=msgs))
        elif isinstance(msgs, MessageChain):
            self.extend(msgs)
        elif isinstance(msgs, MessageElement):
            self.append(msgs)
        elif isinstance(msgs, Iterable):
            self.extend(msgs)
            # for msg in msgs:
            #     if isinstance(msg, MessageElement):
            #         self.append(msg)
            #     else:
            #         raise TypeError(f'{msg} is not a valid MessageElement !')
        else:
            raise ValueError(f'Not a valid MessageChain: {msgs}!')

    def as_plain(self) -> str:
        return ''.join(x.as_plain() for x in self).lstrip()

    def as_display(self) -> str:
        return ''.join(x.as_display() for x in self).lstrip()

    def get_with_index(self,
                       index: int,
                       msg_type: Type[M] = MessageElement,
                       start: int = 0,
                       end: int = 0
                       ) -> Optional[Tuple[M, int]]:
        _index = 0
        if not self:
            return None
        if not (0 <= start < len(self) and 0 <= end <= len(self)):
            raise IndexError(f'{start}:{end} len={len(self)}')
        if not end:
            end = len(self)
        for i in range(start, end):
            msg = self[i]
            if isinstance(msg, msg_type):
                if index == _index:
                    return msg, i
                _index += 1
        else:
            return None

    def get(self,
            index: int,
            msg_type: Type[M] = MessageElement,
            start: int = 0,
            end: int = 0) -> Optional[M]:
        res = self.get_with_index(index, msg_type, start, end)
        return res[0] if res else None

    def get_first_with_index(self,
                             msg_type: Type[M] = MessageElement,
                             start: int = 0,
                             end: int = 0
                             ) -> Optional[Tuple[M, int]]:
        return self.get_with_index(0, msg_type, start, end)

    def get_first(self,
                  msg_type: Type[M] = MessageElement,
                  start: int = 0,
                  end: int = 0
                  ) -> Optional[M]:
        return self.get(0, msg_type, start, end)

    # def __getitem__(self, item):
    #     pass

    def __eq__(self, other):
        if isinstance(other, MessageChain) and len(self) == len(other):
            for a, b in zip(self, other):
                if (not isinstance(a, Meta) or not isinstance(b, Meta)) and a != b:
                    return False
            return True
        else:
            return False

    def copy(self) -> "MessageChain":
        # return MessageChain(filter(lambda x: not isinstance(x, Meta), self))
        return copy.deepcopy(self)

    async def to(self, bot: "Optional[BotSession]", **kwargs) -> "MessageChain":
        """Convert universal message into bot dependent message

        :return:
        """
        chain = MessageChain()
        for msg in self:
            msg_raw = await msg.to(bot, **kwargs)
            if msg_raw:
                chain.append(msg_raw)
        return chain

    async def raw(self) -> "MessageChain":
        """Convert bot dependent message into universal raw message

        :return:
        """
        return await self.to(None)


@dataclass
class Meta(MessageElement):
    type: MessageType = field(default=MessageType.Meta, init=False)


@dataclass
class Quote(MessageElement):
    type: MessageType = field(default=MessageType.Quote, init=False)
    id: MessageIdType
    # senderId: int
    # targetId: int
    # groupId: int
    origin: MessageChain = None

    def as_display(self) -> str:
        return f'[引用]'

    def __eq__(self, other):
        return isinstance(other, Quote) and self.id == other.id


@dataclass
class Plain(MessageElement):
    type: MessageType = field(default=MessageType.Plain, init=False)
    text: str

    def as_plain(self) -> str:
        return self.text

    def as_plain(self) -> str:
        return self.text

    def as_display(self) -> str:
        return self.text

    def __eq__(self, other):
        return isinstance(other, Plain) and self.text == other.text


@dataclass
class At(MessageElement):
    type: MessageType = field(default=MessageType.At, init=False)
    target: ContactIdType

    def as_display(self) -> str:
        return f'@{self.target}'

    def __eq__(self, other):
        return isinstance(other, At) and self.target == other.target


@dataclass
class AtAll(MessageElement):
    type: MessageType = field(default=MessageType.AtAll, init=False)

    def as_display(self) -> str:
        return f'@全体成员'

    def __eq__(self, other):
        return isinstance(other, AtAll)


@dataclass
class Face(MessageElement):
    type: MessageType = field(default=MessageType.Face, init=False)
    id: int

    def as_display(self) -> str:
        return f'[表情]'

    def __eq__(self, other):
        return isinstance(other, Face) and self.id == other.id


@dataclass
class Image(MessageElement):
    type: MessageType = field(default=MessageType.Image, init=False)
    # id: Optional[ImageIdType]
    hash: Optional[str] = None
    url: Optional[str] = None
    content: Optional[bytes] = None

    def __post_init__(self):
        if self.content and not self.hash:
            self.hash = hashlib.md5(self.content).hexdigest()

    def set_content(self, value):
        self.content = value
        if value:
            self.hash = hashlib.md5(self.content).hexdigest()

    def as_display(self) -> str:
        return f'[图片]'

    def __eq__(self, other):
        return isinstance(other, Image) and any((
            self.hash and self.hash == other.hash,
            self.url and self.url == other.url,
            self.content and self.content == other.content
        ))


@dataclass
class Voice(MessageElement):
    type: MessageType = field(default=MessageType.Voice, init=False)
    # id: Optional[VoiceIdType]
    hash: Optional[str] = None
    url: Optional[str] = None
    content: Optional[bytes] = None

    def as_display(self) -> str:
        return f'[语音]'

    def __eq__(self, other):
        return isinstance(other, Voice) and any((
            self.hash and self.hash == other.hash,
            self.url and self.url == other.url,
            self.content and self.content == other.content
        ))


@dataclass
class App(MessageElement):
    type: MessageType = field(default=MessageType.App, init=False)
    content: dict = None

    def as_display(self) -> str:
        return f'[小程序]'


@dataclass
class Xml(MessageElement):
    type: MessageType = field(default=MessageType.Xml, init=False)
    content: str

    def as_display(self) -> str:
        return f'[Xml]'



@dataclass
class ForwardNode():
    id: MessageIdType = None
    name: str = None
    qq: ContactIdType = None
    content: MessageChain = None


@dataclass
class Forward(MessageElement):
    type: MessageType = field(default=MessageType.Forward, init=False)
    content: List[ForwardNode]

    def as_display(self) -> str:
        return f'[合并转发消息]'


@dataclass
class Unknown(MessageElement):
    type: MessageType = field(default=MessageType.Unknown, init=False)


MessageElement_T = Union[MessageElement, str]
Message_T = Union[MessageElement_T, List[MessageElement_T]]
