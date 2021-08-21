import asyncio
from dataclasses import dataclass, field
from typing import *

from fsm import events
from fsm.actions import Action
from fsm.finite_state_machine import NState, epsilon
from fsm.regular_expressions import RegularExpression

from queue import Queue


@dataclass(frozen=True)
class DState:
    transitions: dict[events.Event, Tuple['DState', set[Action]]] = \
        field(default_factory=dict)

    def __hash__(self):
        return id(self)


@dataclass(frozen=True)
class DFSMachine:
    initial_actions: set[Action]
    start: DState

    @staticmethod
    def from_n_state(n_start: NState) -> 'DFSMachine':
        un_processed: Queue[frozenset[NState]] = Queue()
        states_dict: dict[frozenset[NState], DState] = {}

        def follow_epsilon_transitions(n_states: frozenset[NState]) -> Tuple[set[Action], frozenset[NState]]:
            unexplored: set[NState] = set(n_states)
            explored: set[NState] = set()

            actions: set[Action] = set()

            while unexplored:
                explored.update(unexplored)

                actions.update(
                    action
                    for n_state in unexplored
                    for action_set in n_state.transitions.get(epsilon, {}).values()
                    for action in action_set
                )

                unexplored = {
                    new_n_state
                    for n_state in unexplored
                    for new_n_state in n_state.transitions.get(epsilon, {}).keys()
                    if new_n_state not in explored
                }
            return actions, frozenset(explored)

        def n_state_set_to_d_state(n_states: frozenset[NState]) -> Tuple[set[Action], DState]:
            actions, n_states = follow_epsilon_transitions(n_states)

            if n_states not in states_dict:
                new_d_state = DState()
                un_processed.put(n_states)

                states_dict[n_states] = new_d_state

            return actions, states_dict[n_states]

        initial_actions, start_state = n_state_set_to_d_state(frozenset({n_start}))

        while not un_processed.empty():
            n_states = un_processed.get()
            d_state = states_dict[n_states]

            next_events: set[events.Event] = {
                event
                for n_states in n_states
                for event in n_states.transitions.keys()
                if event != epsilon
            }

            for event in next_events:
                next_transitions: list[dict[NState, set[Action]]] = [
                    n_state.transitions[event] for n_state in n_states
                    if event in n_state.transitions
                ]
                next_n_states: set[NState] = {
                    n_state
                    for transitions in next_transitions
                    for n_state in transitions.keys()
                }
                actions1: set[Action] = {
                    action
                    for transitions in next_transitions
                    for actions in transitions.values()
                    for action in actions
                }
                actions2, next_d_state = n_state_set_to_d_state(frozenset(next_n_states))

                d_state.transitions[event] = (next_d_state, actions1 | actions2)

        return DFSMachine(initial_actions, start_state)

    @classmethod
    def from_regular_expression(cls, regex: RegularExpression):
        return cls.from_n_state(regex.to_fsm().start)

    async def run(self):
        for action in self.initial_actions:
            await action.run()

        state = self.start

        while state.transitions:
            event_tasks: dict[asyncio.Task, events.Event] = {
                asyncio.create_task(event.await_event()): event
                for event in state.transitions
            }

            try:

                done, pending = await asyncio.wait(event_tasks, return_when=asyncio.FIRST_COMPLETED)

                for pending_task in pending:
                    pending_task.cancel()

                first_task = next(iter(done))
                first_event = event_tasks[first_task]

                # go to next state
                state, actions = state.transitions[first_event]
                # do actions
                for action in actions:
                    await action.run()
            except asyncio.CancelledError as e:
                for task in event_tasks:
                    if not task.cancelled():
                        task.cancel()

                raise e
