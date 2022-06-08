import copy
import hashlib
import random
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum

import ajenga
from ajenga.message.code import StructCode, escape, unescape
from ajenga.models import ContactIdType
from ajenga.typing import (TYPE_CHECKING, ClassVar, Iterable, List, Optional,
                           Tuple, Type, TypeVar, Union)

if TYPE_CHECKING:
    from ajenga.app import BotSession

RefererIdType = Optional[int]
MessageIdType = int
ImageIdType = str
VoiceIdType = str


class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class MessageType(Enum):
    Meta = "Meta"
    Plain = "Plain"
    At = "At"
    AtAll = "AtAll"
    Face = "Face"
    Image = "Image"
    Quote = "Quote"

    Voice = "Voice"
    File = "File"
    App = "App"
    Json = "Json"
    Xml = "Xml"

    Forward = "Forward"

    # Not fully supported yet
    # FlashImage = "FlashImage"
    # Poke = "Poke"

    Unknown = "Unknown"


@dataclass
class MessageElement(StructCode):
    __message_type__: ClassVar[MessageType] = ...

    referer: RefererIdType = field(default=None, init=False)

    @classproperty
    def type(cls) -> MessageType:
        return cls.__message_type__

    def copy(self):
        return copy.deepcopy(self)

    @classmethod
    def decode_it(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    async def raw(self) -> "Optional[MessageElement]":
        """Convert bot dependent message into universal raw message

        :return:
        """
        self.referer = None
        return self

    async def to(self, bot: "Optional[BotSession]",
                 **kwargs) -> "Optional[MessageElement]":
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


class MessageChain(List[MessageElement], StructCode):
    __struct_type__ = StructCode._LIST_TYPE

    def __init__(self,
                 msgs: Union[str, MessageElement,
                             Iterable[MessageElement]] = ...):
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

    def encode(self) -> str:
        return ''.join(x.encode() for x in self).lstrip()

    @classmethod
    def decode_it(cls, l):
        return cls(l)

    def get_with_index(self,
                       index: int,
                       msg_type: Type[M] = MessageElement,
                       start: int = 0,
                       end: int = 0) -> Optional[Tuple[M, int]]:
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
                             end: int = 0) -> Optional[Tuple[M, int]]:
        return self.get_with_index(0, msg_type, start, end)

    def get_first(self,
                  msg_type: Type[M] = MessageElement,
                  start: int = 0,
                  end: int = 0) -> Optional[M]:
        return self.get(0, msg_type, start, end)

    # def __getitem__(self, item):
    #     pass

    def __eq__(self, other):
        if isinstance(other, MessageChain) and len(self) == len(other):
            for a, b in zip(self, other):
                if (not isinstance(a, Meta)
                        or not isinstance(b, Meta)) and a != b:
                    return False
            return True
        else:
            return False

    def copy(self) -> "MessageChain":
        # return MessageChain(filter(lambda x: not isinstance(x, Meta), self))
        return copy.deepcopy(self)

    async def to(self, bot: "Optional[BotSession]",
                 **kwargs) -> "MessageChain":
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
    __message_type__ = MessageType.Meta


@dataclass
class Quote(MessageElement):
    __message_type__ = MessageType.Quote
    __struct_type__ = "core:quote"
    __struct_fields__ = ("id", )

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
    __message_type__ = MessageType.Plain
    __struct_type__ = ("core:plain", StructCode._STR_TYPE)
    __struct_fields__ = ("text", )

    text: str

    def as_plain(self) -> str:
        return self.text

    def as_display(self) -> str:
        return self.text

    def encode(self):
        return escape(self.text)

    def __eq__(self, other):
        return isinstance(other, Plain) and self.text == other.text

    @staticmethod
    def _insert_seq(seq, x):
        for i in seq:
            if '\u4e00' <= i <= '\u9fa5':
                if random.random() < 0.2:
                    yield x
            yield i

    def _insert_zwsp(self) -> "Plain":
        zwsp = '\ufeff'
        self.text = ''.join(self._insert_seq(self.text, zwsp))
        return self

    async def to(self, bot: "Optional[BotSession]",
                 **kwargs) -> "Optional[MessageElement]":
        """Convert universal message into bot dependent message

        :return:
        """
        if bot is None:
            return await self.raw()
        if getattr(ajenga.config, "ENABLE_INSERT_ZWSP",
                   False) and self.referer == None:
            return await bot.wrap_message(self.copy()._insert_zwsp(), **kwargs)
        else:
            return await bot.wrap_message(self, **kwargs)


@dataclass
class At(MessageElement):
    __message_type__ = MessageType.At
    __struct_type__ = "core:at"
    __struct_fields__ = ("target", )

    target: ContactIdType

    def as_display(self) -> str:
        return f'@{self.target}'

    def __eq__(self, other):
        return isinstance(other, At) and self.target == other.target


@dataclass
class AtAll(MessageElement):
    __message_type__ = MessageType.AtAll
    __struct_type__ = "core:atall"
    __struct_fields__ = ()

    def as_display(self) -> str:
        return f'@全体成员'

    def __eq__(self, other):
        return isinstance(other, AtAll)


@dataclass
class Face(MessageElement):
    __message_type__ = MessageType.Face
    __struct_type__ = "core:face"
    __struct_fields__ = ("id", )

    id: int

    def as_display(self) -> str:
        return f'[表情]'

    def __eq__(self, other):
        return isinstance(other, Face) and self.id == other.id


@dataclass
class Image(MessageElement):
    __message_type__ = MessageType.Image
    __struct_type__ = "core:image"
    __struct_fields__ = ("url", "hash")

    # id: Optional[ImageIdType]
    hash: Optional[str] = None
    url: Optional[str] = None
    content: Optional[bytes] = field(default=None, repr=False)

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
        return isinstance(other, Image) and any(
            (self.hash and self.hash == other.hash, self.url and self.url
             == other.url, self.content and self.content == other.content))


@dataclass
class Voice(MessageElement):
    __message_type__ = MessageType.Voice
    __struct_type__ = "core:voice"
    __struct_fields__ = ("url", "hash")

    # id: Optional[VoiceIdType]
    hash: Optional[str] = None
    url: Optional[str] = None
    content: Optional[bytes] = field(default=None, repr=False)

    def as_display(self) -> str:
        return f'[语音]'

    def __eq__(self, other):
        return isinstance(other, Voice) and any(
            (self.hash and self.hash == other.hash, self.url and self.url
             == other.url, self.content and self.content == other.content))


@dataclass
class File(MessageElement):
    __message_type__ = MessageType.File
    __struct_type__ = "core:file"
    __struct_fields__ = ("url", "hash", "name")

    # id: Optional[VoiceIdType]
    hash: Optional[str] = None
    url: Optional[str] = None
    name: Optional[str] = None
    content: Optional[bytes] = field(default=None, repr=False)

    def __post_init__(self):
        if self.content and not self.hash:
            self.hash = hashlib.md5(self.content).hexdigest()

    def set_content(self, value):
        self.content = value
        if value:
            self.hash = hashlib.md5(self.content).hexdigest()

    def as_display(self) -> str:
        return f'[文件]'

    def __eq__(self, other):
        return isinstance(other, File) and any(
            (self.hash and self.hash == other.hash, self.url
             and self.url == other.url, self.name and self.name == other.name,
             self.content and self.content == other.content))


@dataclass
class App(MessageElement):
    __message_type__ = MessageType.App
    __struct_type__ = "core:app"
    __struct_fields__ = ("content", )

    content: dict = None

    def encode(self) -> str:
        import json
        return f"[{self.__struct_type__},content={escape(json.dumps(self.content))}]"

    @classmethod
    def decode_it(cls, content):
        import json
        return cls(content=json.loads(content))

    def as_display(self) -> str:
        return f'[小程序]'


@dataclass
class Xml(MessageElement):
    __message_type__ = MessageType.Xml
    __struct_type__ = "core:xml"
    __struct_fields__ = ("content", )

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
    __message_type__ = MessageType.Forward
    __struct_type__ = "core:forward"
    __struct_fields__ = ()

    content: List[ForwardNode]

    def as_display(self) -> str:
        return f'[合并转发消息]'


@dataclass
class Unknown(MessageElement):
    __message_type__ = MessageType.Unknown
    __struct_fields__ = ()


MessageElement_T = Union[MessageElement, str]
Message_T = Union[MessageElement_T, List[MessageElement_T], MessageChain]
