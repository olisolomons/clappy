import abc
from dataclasses import dataclass, field

from fsm.actions import Action
from fsm.events import Event as BaseEvent
from fsm.finite_state_machine import NFSMachine, NState, epsilon


class RegularExpression(abc.ABC):
    @abc.abstractmethod
    def to_fsm(self) -> NFSMachine:
        pass

    def __or__(self, other):
        return Or([self, other])

    def __rshift__(self, other):
        if isinstance(other, Sequence):
            return Sequence([self, *other.expressions])
        else:
            return Sequence([self, other])


@dataclass(frozen=True)
class Event(RegularExpression):
    event: BaseEvent
    actions: set[Action] = frozenset()

    def to_fsm(self) -> NFSMachine:
        start = NState()
        end = NState()

        start.add_transition(self.event, end, self.actions)

        return NFSMachine(start, end)


@dataclass(frozen=True)
class Many(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> NFSMachine:
        return Or([Some(self.expression), Sequence([])]).to_fsm()


@dataclass(frozen=True)
class Some(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> NFSMachine:
        machine = self.expression.to_fsm()
        machine.end.add_transition(epsilon, machine.start)

        return machine


@dataclass(frozen=True)
class Or(RegularExpression):
    alternatives: list[RegularExpression]

    def to_fsm(self) -> NFSMachine:
        start = NState()
        end = NState()

        for alternative in self.alternatives:
            machine = alternative.to_fsm()

            start.add_transition(epsilon, machine.start)
            machine.end.add_transition(epsilon, end)

        return NFSMachine(start, end)


@dataclass(frozen=True)
class Sequence(RegularExpression):
    expressions: list[RegularExpression]

    def to_fsm(self) -> NFSMachine:
        start = NState()
        end = start
        for expression in self.expressions:
            machine = expression.to_fsm()
            end.add_transition(epsilon, machine.start)
            end = machine.end

        return NFSMachine(start, end)

    def __rshift__(self, other):
        if isinstance(other, Sequence):
            return Sequence([*self.expressions, *other.expressions])
        else:
            return Sequence([*self.expressions, other])


@dataclass(frozen=True)
class OptionalExpr(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> NFSMachine:
        return Or([self.expression, Sequence([])]).to_fsm()
