import asyncio
import time
from dataclasses import dataclass

from ajenga import app, router
from ajenga.event import Event, EventProvider, EventType
from ajenga.message import MessageIdType, Quote
from ajenga.provider import BotSession
from ajenga.router import std
from ajenga.router.keystore import KeyStore
from ajenga.router.models import Executor, Graph, Priority, Task, TerminalNode
from ajenga.router.state import RouteState
from ajenga.typing import Any, List, Tuple

_CANDIDATES_KEY = '_wakeup_candidates'
_SUSPEND_OTHER_KEY = 'suspend_other'
_SUSPEND_NEXT_PRIORITY_KEY = 'suspend_next_priority'


class SchedulerSource(EventProvider):
    pass


_scheduler_source = SchedulerSource()


@dataclass
class SchedulerEvent(Event):
    type: EventType = EventType.Unknown


class _ContextWrapperMeta(type):
    def __getattr__(self, item):
        state, mapping = Task.current().args
        return state.store[
            mapping[item]] if item in mapping else state.store[item]

    # def __setattr__(self, key, value):
    #    Task.current().args[0].store[key] = value

    def __getitem__(self, item):
        if isinstance(item, int):
            try:
                return Task.current().args[0].args[item]
            except:
                raise ValueError("Cannot find specified positional argument")
        return self.__getattr__(item)

    # def __setitem__(self, key, value):
    #     self.__setattr__(key, value)


class _ContextWrapper(metaclass=_ContextWrapperMeta):
    @classmethod
    async def wait_until(
        cls,
        graph: Graph,
        *,
        timeout: float = 3600,
        suspend_other: bool = False,
        suspend_next_priority: bool = False,
    ):

        task = Task.current()
        task.state[_SUSPEND_OTHER_KEY] = suspend_other
        task.state[_SUSPEND_NEXT_PRIORITY_KEY] = suspend_next_priority

        async def _check_timeout():
            cur_time = time.time()
            if cur_time - task.last_active_time > timeout:
                app.engine.unsubscribe_terminals([_dumpy_node])
                if task.paused:
                    task.raise_(TimeoutError())
                return False
            return True

        async def _add_candidate(_state: RouteState, _store: KeyStore):
            if _CANDIDATES_KEY not in _store:
                _store[_CANDIDATES_KEY] = []
            _store[_CANDIDATES_KEY].append(
                (task, _dumpy_node, (_state, _state.build())))

        @app.on(std.if_(_check_timeout) & graph & std.process(_add_candidate))
        @std.handler(priority=Priority.Never, count_finished=False)
        async def _dumpy_node():
            pass

        async def _set_timeout():
            await asyncio.sleep(timeout)
            await app.handle_event(_scheduler_source, SchedulerEvent())

        asyncio.create_task(_set_timeout())

        await task.pause()

    @classmethod
    async def wait_next(
        cls,
        graph: Graph = std.true,
        *,
        timeout: float = 3600,
        suspend_other: bool = False,
        suspend_next_priority: bool = False,
    ):
        return await cls.wait_until(
            router.message.same_event_as(this.event) & graph,
            timeout=timeout,
            suspend_other=suspend_other,
            suspend_next_priority=suspend_next_priority)

    @classmethod
    async def wait_quote(
        cls,
        message_id: MessageIdType = ...,
        bot: BotSession = ...,
        graph: Graph = std.true,
        *,
        timeout: float = 3600,
        suspend_other: bool = False,
        suspend_next_priority: bool = False,
    ):
        message_id = this.event.message_id if message_id is ... else message_id
        bot = this.bot if bot is ... else bot
        return await cls.wait_until(
            router.message.has(Quote)
            & std.if_(lambda event, source: event.message.get_first(Quote).id
                      == message_id and source == bot)
            & graph,
            timeout=timeout,
            suspend_other=suspend_other,
            suspend_next_priority=suspend_next_priority)

    @classmethod
    def suspend_next_priority(cls):
        Executor.current().next_priority = False


@app.on(std.true)
@std.handler(priority=Priority.Wakeup, count_finished=False)
async def _check_wait(_store: KeyStore):
    def _wakeup(candi, node, args):
        candi.priority = Task.current().priority
        candi.args = args
        Executor.current().add_task(candi)
        app.engine.unsubscribe_terminals([node])

    candidates: List[Tuple[Task, TerminalNode,
                           Any]] = _store.get(_CANDIDATES_KEY, [])
    candidates.sort(key=lambda e: e[0].last_active_time)

    _suspend_other = False
    _suspend_next_priority = False

    while not _suspend_other and candidates:
        candidate, dumpy_node, arguments = candidates.pop()
        _suspend_other = candidate.state[_SUSPEND_OTHER_KEY]
        _suspend_next_priority |= candidate.state[_SUSPEND_NEXT_PRIORITY_KEY]
        _wakeup(candidate, dumpy_node, arguments)

    if _suspend_next_priority:
        Executor.current().next_priority = False


class TimeoutError(Exception):
    pass


this = _ContextWrapper
