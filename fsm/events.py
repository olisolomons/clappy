import abc
import asyncio
from dataclasses import dataclass, field


class Event(abc.ABC):
    @abc.abstractmethod
    async def await_event(self):
        pass


@dataclass(frozen=True)
class Clap(Event):
    short_clap_queue: asyncio.Queue = field(repr=False, compare=False)
    long_clap_queue: asyncio.Queue = field(repr=False, compare=False)

    is_long: bool

    async def await_event(self):
        if self.is_long:
            await self.long_clap_queue.get()
        else:
            await self.short_clap_queue.get()


@dataclass(frozen=True)
class Wait(Event):
    seconds: float

    async def await_event(self):
        await asyncio.sleep(self.seconds)