import asyncio
from dataclasses import dataclass, field

from fsm.events import OnNotify
from fsm.actions import Func
from fsm import actions
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

    def action(self) -> actions.Action:
        return Func(self.notify, self.tag)

    def event_re(self, actions=frozenset()) -> rex.Event:
        return rex.Event(self.event(), actions)
