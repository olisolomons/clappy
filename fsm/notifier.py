import asyncio
from dataclasses import dataclass, field

from fsm.events import OnNotify
from fsm.actions import Func
import fsm.regular_expressions as rex

@dataclass(frozen=True)
class Notifier:
    tag : str
    condition: asyncio.Condition = field(repr=False, compare=False, default_factory=asyncio.Condition)

    def event(self):
        return OnNotify(self.condition, self.tag)

    async def notify(self):
        async with self.condition:
            self.condition.notify_all()
        await asyncio.sleep(0.05)

    def action(self):
        return Func(self.notify, self.tag)

    def event_re(self, actions=None):
        return rex.Event(self.event(), set() if actions is None else actions)
