import asyncio
from dataclasses import dataclass, field
from enum import Enum

from fsm.actions import Action
from fsm import events

from typing import *


class EpsilonTransition(Enum):
    """
    A transition that is taken immediately, without waiting for an event. It is can be optimised away.
    """
    epsilon = 0


epsilon = EpsilonTransition.epsilon


@dataclass(frozen=True)
class FSMNode:
    transitions: dict[Union[events.Event, EpsilonTransition], dict['FSMNode', set[Action]]] = \
        field(default_factory=lambda: {})

    def __hash__(self):
        return id(self)

    def add_transition(self,
                       event: Union[events.Event, EpsilonTransition],
                       new_state: 'FSMNode',
                       actions: Iterable[Action] = None):
        self.transitions \
            .setdefault(event, dict()) \
            .setdefault(new_state, set()) \
            .update(actions if actions is not None else set())


@dataclass(frozen=True)
class FSMachine:
    start: FSMNode
    end: FSMNode


async def wait(t):
    try:
        await asyncio.sleep(t)
        print(f'done, {t=}')
    except asyncio.CancelledError as e:
        print(f'cancelled {t=}')
        print(e)


async def race(aws):
    tasks = [asyncio.create_task(co) for co in aws]
    task_map = {task: i for i, task in enumerate(tasks)}
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
        print('cancelling a task')
    print(f'{tasks.index(list(done)[0])=}')
    print(f'{task_map[list(done)[0]]=}')


async def a():
    await race([wait(2), wait(5), wait(2.1)])
    print('done a')


async def main():
    await asyncio.wait([asyncio.create_task(a()), asyncio.create_task(wait(7))])


if __name__ == '__main__':
    asyncio.run(main())
