import abc
from dataclasses import dataclass, field

from fsm.actions import Action
from fsm.events import Event as BaseEvent
from fsm.finite_state_machine import FSMachine, FSMNode, epsilon


class RegularExpression(abc.ABC):
    @abc.abstractmethod
    def to_fsm(self) -> FSMachine:
        pass

    def __or__(self, other):
        return Or([self, other])

    def __rshift__(self, other):
        return Sequence([self, other])


@dataclass(frozen=True)
class Event(RegularExpression):
    event: BaseEvent
    actions: set[Action] = field(default_factory=set)

    def to_fsm(self) -> FSMachine:
        start = FSMNode()
        end = FSMNode()

        start.add_transition(self.event, end, self.actions)

        return FSMachine(start, end)


@dataclass(frozen=True)
class Many(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> FSMachine:
        return Or([Some(self.expression), Sequence([])]).to_fsm()


@dataclass(frozen=True)
class Some(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> FSMachine:
        machine = self.expression.to_fsm()
        machine.end.add_transition(epsilon, machine.start)

        return machine


@dataclass(frozen=True)
class Or(RegularExpression):
    alternatives: list[RegularExpression]

    def to_fsm(self) -> FSMachine:
        start = FSMNode()
        end = FSMNode()

        for alternative in self.alternatives:
            machine = alternative.to_fsm()

            start.add_transition(epsilon, machine.start)
            machine.end.add_transition(epsilon, end)

        return FSMachine(start, end)


@dataclass(frozen=True)
class Sequence(RegularExpression):
    expressions: list[RegularExpression]

    def to_fsm(self) -> FSMachine:
        start = FSMNode()
        end = start
        for expression in self.expressions:
            machine = expression.to_fsm()
            end.add_transition(epsilon, machine.start)
            end = machine.end

        return FSMachine(start, end)


@dataclass(frozen=True)
class OptionalExpr(RegularExpression):
    expression: RegularExpression

    def to_fsm(self) -> FSMachine:
        return Or([self.expression, Sequence([])]).to_fsm()
