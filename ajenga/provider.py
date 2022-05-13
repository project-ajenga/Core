import asyncio

from ajenga.app import handle_event
from ajenga.event import (CustomEvent, Event, EventProvider,
                          FriendMessageEvent, GroupMessageEvent, MessageEvent,
                          MetaEvent, TempMessageEvent)
from ajenga.message import At, Message_T, MessageChain, MessageElement
from ajenga.models import ContactIdType
from ajenga.protocol import Api


class MetaProvider(EventProvider):
    async def send(self, event: MetaEvent):
        return await handle_event(self, event)

    def send_nowait(self, event: MetaEvent):
        return asyncio.create_task(handle_event(self, event))

    @property
    def type(self) -> str:
        return "meta"


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
    def api(self) -> Api:
        raise NotImplementedError

    async def send(self,
                   event: MessageEvent,
                   message: Message_T,
                   at_sender: bool = False):
        if at_sender and isinstance(event, GroupMessageEvent):
            message = MessageChain(message)
            message.insert(0, At(event.sender.qq))

        return await self._send(event, message)

    async def _send(self, event: MessageEvent, message: Message_T):
        if isinstance(event, GroupMessageEvent):
            return await self.api.send_group_message(group=event.group,
                                                     message=message)
        elif isinstance(event, FriendMessageEvent):
            return await self.api.send_friend_message(qq=event.sender.qq,
                                                      message=message)
        elif isinstance(event, TempMessageEvent):
            return await self.api.send_temp_message(qq=event.sender.qq,
                                                    group=event.group,
                                                    message=message)

    async def wrap_message(self, message: MessageElement,
                           **kwargs) -> MessageElement:
        raise NotImplementedError


class ChannelProvider(EventProvider):
    def __init__(self, channel) -> None:
        super().__init__()
        self.channel = channel

    async def send(self, **kwargs):
        event = CustomEvent(self.channel, **kwargs)
        return await handle_event(self, event)

    def send_nowait(self, **kwargs):
        event = CustomEvent(self.channel, **kwargs)
        return asyncio.create_task(handle_event(self, event))

    @property
    def type(self) -> str:
        return "channel"
