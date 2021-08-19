import fsm.regular_expressions as rex
from fsm.events import Wait
from fsm.actions import Print

test1 = rex.Event(Wait(3), {Print('hello')}) >> rex.Event(Wait(3), {Print('world')}) | rex.Event(Wait(1))


def main():
    print(test1)


if __name__ == '__main__':
    main()
