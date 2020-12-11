import asyncio

from ajenga.event import Event
from ajenga.event import EventProvider
from ajenga.event import FriendMessageEvent
from ajenga.event import GroupMessageEvent
from ajenga.event import MessageEvent
from ajenga.event import MetaEvent
from ajenga.event import TempMessageEvent
from ajenga.message import At
from ajenga.message import MessageChain
from ajenga.message import MessageElement
from ajenga.message import Message_T
from ajenga.models import ContactIdType
from ajenga.protocol import Api
from ajenga.app import handle_event


class MetaProvider(EventProvider):

    async def send(self, event: MetaEvent):
        await handle_event(self, event)


meta_provider = MetaProvider()


class BotSession(EventProvider):

    @property
    def qq(self) -> ContactIdType:
        raise NotImplementedError

    async def handle_event(self, event: Event):
        return await handle_event(self, event, bot=self)

    def handle_event_nowait(self, event: Event) -> asyncio.Task:
        return asyncio.create_task(handle_event(self, event, bot=self))

    def __str__(self):
        return f'<{type(self).__name__}: {id(self)}>'

    def __repr__(self):
        return f'<{type(self).__name__}: {id(self)}>'

    @property
    def ok(self) -> bool:
        raise NotImplementedError

    @property
    def asgi(self):
        raise NotImplementedError

    @property
    def api(self) -> Api:
        raise NotImplementedError

    async def send(self, event: MessageEvent, message: Message_T, at_sender: bool = False):
        if at_sender and isinstance(event, GroupMessageEvent):
            message = MessageChain(message)
            message.insert(0, At(event.sender.qq))

        return await self._send(event, message)

    async def _send(self, event: MessageEvent, message: Message_T):
        if isinstance(event, GroupMessageEvent):
            return await self.api.send_group_message(group=event.group, message=message)
        elif isinstance(event, FriendMessageEvent):
            return await self.api.send_friend_message(qq=event.sender.qq, message=message)
        elif isinstance(event, TempMessageEvent):
            return await self.api.send_temp_message(qq=event.sender.qq, group=event.group, message=message)

    async def wrap_message(self, message: MessageElement, **kwargs) -> MessageElement:
        raise NotImplementedError
