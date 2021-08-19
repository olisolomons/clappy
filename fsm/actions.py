import abc
from dataclasses import dataclass


class Action(abc.ABC):
    @abc.abstractmethod
    def run(self):
        pass


@dataclass(frozen=True)
class Print(Action):
    print_data: str

    def run(self):
        print(self.print_data)