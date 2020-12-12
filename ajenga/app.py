from ajenga.typing import Dict
from ajenga.typing import Optional

from ajenga.event import Event
from ajenga.event import EventProvider
from ajenga.log import logger
from ajenga.models import ContactIdType
from ajenga.routing.engine import Engine


async def handle_event(source: EventProvider, event: Event, **kwargs):
    """Handle a event received from protocol

    To avoid blocking awaiting, creating a task to run this

    :param source:
    :param event:
    :return:
    """
    if not isinstance(event, Event):
        logger.error(f'A non-event {event} passed to handle_event!')
        return

    logger.debug(f'Handling {event.type} {event}')

    res = []

    async for result in engine.forward(event=event, source=source, **kwargs):
        if isinstance(result, Exception):
            try:
                raise result
            except Exception as e:
                logger.error(f'Error handling event {event} {e}')
                logger.exception(e)
        res.append(result)

    return res


from ajenga.provider import BotSession

engine = Engine()
_sessions: Dict[ContactIdType, BotSession] = {}
_sessions_inverse: Dict[int, ContactIdType] = {}

on = engine.on


def register_session(session: BotSession, qq: ContactIdType = None):
    qq = qq or session.qq
    if qq in _sessions:
        logger.warning(f'A session already registered to {qq} !')
    _sessions[qq] = session
    _sessions_inverse[id(session)] = qq


def unregister_session(qq: ContactIdType) -> bool:
    if qq in _sessions:
        try:
            del _sessions_inverse[id(_sessions[qq])]
            del _sessions[qq]
            return True
        except Exception as e:
            logger.critical(e, exc_info=True)
            return False
    else:
        return False


def get_session(qq: ContactIdType) -> Optional[BotSession]:
    return _sessions.get(qq)


def get_sessions() -> Dict[ContactIdType, BotSession]:
    return _sessions.copy()
