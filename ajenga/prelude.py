from ajenga.event import MessageEvent
from ajenga.message import Message_T
from ajenga.ctx import this


def _reply(self, message: Message_T, **kwargs):
    return this.bot.send(self, message, **kwargs)


setattr(MessageEvent, 'reply', _reply)
