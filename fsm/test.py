from functools import partial

import fsm.regular_expressions as rex
from fsm.events import Wait
from fsm.notifier import Notifier
from fsm.actions import Print
import asyncio
from fsm.deterministic_finite_state_machine import DFSMachine

test1 = rex.Event(Wait(3), {Print('hello')}) >> rex.Event(Wait(3), {Print('world')}) | rex.Event(Wait(1))

clap = Notifier('clap')
# play|pause; pause, left*; left*; right*
# ss = play|pause, sl(s|l)* = pause+left, ls(s|l)*
play_pause = clap.event_re() >> (
        rex.Event(Wait(0.75)) >> rex.Event(Wait(1.25))
        | clap.event_re() >> (
                rex.Event(Wait(0.75)) >> rex.Event(Wait(1.25))
                | clap.event_re({Print('play_pause')})
        )
)
skip_left = clap.event_re() >> (
        rex.Event(Wait(0.75)) >> rex.Event(Wait(1.25))
        | clap.event_re() >> (
                rex.Event(Wait(0.75)) >> (
                rex.Event(Wait(1.25))
                | clap.event_re({Print('play_pause')}) >>
                rex.Many(
                    clap.event_re({Print('left')})
                ) >>
                rex.Event(Wait(2))  # this should be re-run for every loop of the "Many", allowing an exit

        )
        )
)

async def main():
    print(f'{play_pause=}')
    print(f'{skip_left=}')
    print(f'{skip_left.to_fsm()=}')

    machine = DFSMachine.from_regular_expression(skip_left | play_pause)

    print(machine)


if __name__ == '__main__':
    asyncio.run(main())
