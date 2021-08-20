import abc
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any


class Action(abc.ABC):
    @abc.abstractmethod
    async def run(self):
        pass


@dataclass(frozen=True)
class Print(Action):
    print_data: str

    async def run(self):
        print(self.print_data)


@dataclass(frozen=True)
class Func(Action):
    func: Callable[[], Awaitable[Any]] = field(repr=False)
    tag : str

    async def run(self):
        await self.func()
