import abc
import asyncio
from dataclasses import dataclass, field


class Event(abc.ABC):
    @abc.abstractmethod
    async def await_event(self):
        pass

    def __rshift__(self, other: 'Event') -> 'Event':
        return Sequence(self, other)


@dataclass(frozen=True)
class Sequence(Event):
    first: Event
    second: Event

    async def await_event(self):
        await self.first.await_event()
        await self.second.await_event()


@dataclass(frozen=True)
class OnNotify(Event):
    condition: asyncio.Condition = field(repr=False, compare=False)
    tag : str

    async def await_event(self):
        async with self.condition:
            await self.condition.wait()


@dataclass(frozen=True)
class Wait(Event):
    seconds: float

    async def await_event(self):
        await asyncio.sleep(self.seconds)
