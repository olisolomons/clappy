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

    def __repr__(self):
        return 'ε'


epsilon = EpsilonTransition.epsilon


@dataclass(frozen=True)
class NState:
    transitions: dict[Union[events.Event, EpsilonTransition], dict['NState', set[Action]]] = \
        field(default_factory=dict)

    def __hash__(self):
        return id(self)

    def add_transition(self,
                       event: Union[events.Event, EpsilonTransition],
                       new_state: 'NState',
                       actions: Iterable[Action] = None):
        self.transitions \
            .setdefault(event, dict()) \
            .setdefault(new_state, set()) \
            .update(actions if actions is not None else set())


@dataclass(frozen=True)
class NFSMachine:
    """
    Non-deterministic finite state machine.
    """
    start: NState
    end: NState
