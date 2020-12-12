from abc import ABC
from ajenga.typing import Generic
from ajenga.typing import List
from ajenga.typing import Optional
from ajenga.typing import TypeVar

from ajenga.event import MessageEvent
from ajenga.message import MessageIdType
from ajenga.message import Message_T
from ajenga.models import ContactIdType
from ajenga.models import Friend
from ajenga.models import Group
from ajenga.models import GroupConfig
from ajenga.models import GroupMember

T = TypeVar('T')


class Code:
    Success = 0
    Unspecified = -1
    Unavailable = -2
    IncorrectArgument = -5
    RequestError = -10
    NetworkError = -20


class ApiResult(Generic[T]):
    _code: int
    _message: str
    _data: T

    def __init__(self, code: int, data: T = None, message: str = None):
        self._code = code
        self._message = message or ''
        self._data = data

    @property
    def code(self) -> int:
        return self._code

    @property
    def message(self) -> str:
        return self._message

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def data(self) -> T:
        return self._data

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)


class MessageSendResult:
    message_id: int

    def __init__(self, message_id: int):
        self.message_id = message_id


class Api(ABC):

    async def send_friend_message(self,
                                  qq: ContactIdType,
                                  message: Message_T,
                                  ) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def send_temp_message(self,
                                qq: ContactIdType,
                                group: ContactIdType,
                                message: Message_T,
                                ) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def send_group_message(self,
                                 group: ContactIdType,
                                 message: Message_T,
                                 ) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def recall(self,
                     message_id: MessageIdType,
                     ) -> ApiResult[None]:
        raise NotImplementedError

    async def get_message(self,
                          message_id: MessageIdType,
                          ) -> ApiResult[MessageEvent]:
        raise NotImplementedError

    async def get_friend_list(self) -> ApiResult[List[Friend]]:
        raise NotImplementedError

    async def get_group_list(self) -> ApiResult[List[Group]]:
        raise NotImplementedError

    async def get_group_member_list(self,
                                    group: ContactIdType,
                                    ) -> ApiResult[List[GroupMember]]:
        raise NotImplementedError

    async def set_group_mute(self,
                             group: ContactIdType,
                             qq: Optional[ContactIdType],
                             duration: Optional[int] = None,
                             ) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_unmute(self,
                               group: ContactIdType,
                               qq: Optional[ContactIdType],
                               ) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_kick(self,
                             group: ContactIdType,
                             qq: ContactIdType,
                             ) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_leave(self,
                              group: ContactIdType,
                              ) -> ApiResult[None]:
        raise NotImplementedError

    async def get_group_config(self,
                               group: ContactIdType,
                               ) -> ApiResult[GroupConfig]:
        raise NotImplementedError

    async def set_group_config(self,
                               group: ContactIdType,
                               config: GroupConfig,
                               ) -> ApiResult[None]:
        raise NotImplementedError

    async def get_group_member_info(self,
                                    group: ContactIdType,
                                    qq: ContactIdType,
                                    ) -> ApiResult[GroupMember]:
        raise NotImplementedError

    async def set_group_member_info(self,
                                    group: ContactIdType,
                                    qq: ContactIdType,
                                    info: GroupMember,
                                    ) -> ApiResult[None]:
        raise NotImplementedError
