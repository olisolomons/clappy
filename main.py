#!/usr/bin/python3
import asyncio
import dataclasses
import functools
from dataclasses import dataclass
import time
from threading import Thread
from typing import Union, Optional, Tuple, Callable

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


@dataclass(frozen=True)
class Press(Action):
    key: str
    device: str
    loop: asyncio.AbstractEventLoop

    async def run(self):
        await self.loop.run_in_executor(None, lambda: press(self.device, self.key))


@dataclass
class CalibrationNotifier:
    notifier: Optional[Notifier] = None
    loop: Optional[asyncio.AbstractEventLoop] = None

    async def make_finished_calibration_notifier(self):
        self.notifier = Notifier('finished_calibration')
        return self.notifier, asyncio.get_event_loop()

    def notify(self, loop: asyncio.AbstractEventLoop):
        asyncio.run_coroutine_threadsafe(self.notifier.notify(), loop)


def generate_regex(clap_notifier: Notifier, data: Tuple[Notifier, asyncio.AbstractEventLoop]) -> rex.RegularExpression:
    finished_calibration: Notifier
    finished_calibration, loop = data

    press_ev: Callable[[str], Press] = functools.partial(Press, device='/dev/input/event3', loop=loop)

    def wait(t):
        return rex.Event(Wait(t))

    timeout = 2
    long_clap_delay = 0.75

    def long(ev):
        return wait(long_clap_delay) >> (
                ev | wait(timeout - long_clap_delay)
        )

    def short(ev):
        return ev | wait(long_clap_delay) >> wait(timeout - long_clap_delay)

    def clap(actions: set[Action] = frozenset()):
        return clap_notifier.event_re(actions | {Print('clap')})

    # .s.s.{play_pause}(.{left})*
    play_pause_left = (
            clap() >>
            short(clap() >>
                  short(
                      clap({Print('play/pause'), press_ev('KEY_PLAYPAUSE')}) >>
                      rex.Many(
                          clap({Print('left'), press_ev('KEY_LEFT')})
                      ) >>
                      wait(timeout)
                  )))
    # .s.l.{left}(.{left})*
    skip_left = (
            clap() >>
            short(clap() >>
                  long(
                      rex.Some(
                          clap({Print('left'), press_ev('KEY_LEFT')})
                      ) >>
                      wait(timeout)
                  )))
    # .l.s.{right}(.{right})*
    skip_right = (
            clap() >>
            long(clap() >>
                 short(
                     rex.Some(
                         clap({Print('right'), press_ev('KEY_RIGHT')})
                     ) >>
                     wait(timeout)
                 )))

    whilst_calibrating = rex.Many(clap()) >> finished_calibration.event_re({Print('start listening!')})

    return whilst_calibrating >> rex.Many(play_pause_left | skip_left | skip_right)


def clappy(verbose: bool = False, threshold: Union[int, str] = 'auto'):
    print('Calibrating')
    use_settings = dataclasses.replace(settings.default_settings, threshold=threshold)
    finished_calibration = CalibrationNotifier()

    clappy_sequence = ClappySequenceRegex(
        generate_regex,
        settings=use_settings,
        make_async_objects=finished_calibration.make_finished_calibration_notifier
    )

    if threshold == 'auto':
        def turn_off_auto_delayed():
            time.sleep(5)
            clappy_sequence.clappy.auto_threshold = False
            threshold = clappy_sequence.clappy.settings.threshold
            print(f'Auto threshold tuning turned off, {threshold=}')

            finished_calibration.notify(clappy_sequence.machine_loop)

        thread = Thread(target=turn_off_auto_delayed)
        thread.start()
    else:
        finished_calibration.notify(clappy_sequence.machine_loop)

    clappy_sequence.listen(verbose=verbose)


if __name__ == '__main__':
    fire.Fire(clappy)
