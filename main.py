#!/usr/bin/python3
import dataclasses
import time
from threading import Thread
from typing import Union

import settings
from clappy_sequence import ClappySequence
from clappy_sequence_regex import ClappySequenceRegex
import subprocess
import fire

import fsm.regular_expressions as rex
from fsm.events import Wait
from fsm.actions import Print, Action
from fsm.notifier import Notifier


def press(device, key):
    for value in (1, 0):
        subprocess.run(
            ['/usr/bin/env',
             'evemu-event',
             device,
             '--type', 'EV_KEY',
             '--code', key,
             '--value', str(value),
             '--sync'
             ]
        )


def generate_regex(clap: Notifier) -> rex.RegularExpression:
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

    return play_pause | skip_left


def clappy(verbose: bool = False, threshold: Union[int, str] = 'auto'):
    print('Listening for claps!')
    use_settings = dataclasses.replace(settings.default_settings, threshold=threshold)

    clappy_sequence = ClappySequenceRegex(generate_regex, settings=use_settings)

    if threshold == 'auto':
        def turn_off_auto_delayed():
            time.sleep(5)
            clappy_sequence.clappy.auto_threshold = False
            threshold = clappy_sequence.clappy.settings.threshold
            print(f'Auto threshold tuning turned off, {threshold=}')

        thread = Thread(target=turn_off_auto_delayed)
        thread.start()

    clappy_sequence.listen(verbose=verbose)


if __name__ == '__main__':
    fire.Fire(clappy)
