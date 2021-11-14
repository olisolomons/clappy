#!/usr/bin/python3
import asyncio
import dataclasses
import functools
from dataclasses import dataclass
import time
from threading import Thread
from typing import Union, Optional, Tuple, Callable

import settings
from clap_sequence_binary import ClapSequenceBinary
from clap_sequence_regex import ClapSequenceRegex
import subprocess
import fire

import fsm.regular_expressions as rex
from fsm.events import Wait
from fsm.actions import Print, Action
from fsm.notifier import Notifier
from websocket_listener import WebSocketListener
from pathlib import Path


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


def set_mic(un_muted: bool):
    subprocess.run(
        ['/usr/bin/env',
         'amixer',
         'set',
         'Capture',
         'cap' if un_muted else 'nocap'
         ], stdout=subprocess.PIPE
    )


@dataclass(frozen=True)
class Press(Action):
    key: str
    device: str
    loop: asyncio.AbstractEventLoop

    async def run(self):
        await self.loop.run_in_executor(None, lambda: press(self.device, self.key))


@dataclass
class ClapProgram:
    finished_calibration: Optional[Notifier] = None
    loop: Optional[asyncio.AbstractEventLoop] = None

    def notify_finished_calibration(self):
        asyncio.run_coroutine_threadsafe(self.finished_calibration.notify(), self.loop)

    async def generate_regex(self, clap_notifier: Notifier) -> rex.RegularExpression:
        self.finished_calibration = Notifier('finished_calibration')
        self.loop = asyncio.get_event_loop()

        press_ev: Callable[[str], Press] = functools.partial(Press, device='/dev/input/event3', loop=self.loop)

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

        whilst_calibrating = rex.Many(clap()) >> self.finished_calibration.event_re({Print('start listening!')})

        return whilst_calibrating >> rex.Many(play_pause_left | skip_left | skip_right)


def clappy(verbose: bool = False, threshold: Union[int, str] = 'auto'):
    print('Calibrating')
    use_settings = dataclasses.replace(settings.default_settings, threshold=threshold)
    clap_program = ClapProgram()

    clappy_sequence = ClapSequenceRegex(
        clap_program.generate_regex,
        settings=use_settings
    )

    if threshold == 'auto':
        def turn_off_auto_delayed():
            time.sleep(5)
            clappy_sequence.clappy.auto_threshold = False
            threshold = clappy_sequence.clappy.settings.threshold
            print(f'Auto threshold tuning turned off, {threshold=}')

            clap_program.notify_finished_calibration()

        thread = Thread(target=turn_off_auto_delayed)
        thread.start()
    else:
        clap_program.notify_finished_calibration()

    set_mic(True)
    clappy_sequence.listen(verbose=verbose)
    set_mic(False)


def websocket():
    key: Callable[[str], None] = functools.partial(press, '/dev/input/event3')

    class App:
        def __init__(self):
            self.use_space = False

        def play_pause(self):
            if self.use_space:
                key('KEY_SPACE')
            else:
                key('KEY_PLAYPAUSE')

        @staticmethod
        def back():
            key('KEY_LEFT')

        @staticmethod
        def forward():
            key('KEY_RIGHT')

        @staticmethod
        def skip():
            key('KEY_S')

        def change_use_space(self, msg):
            self.use_space = msg['value']
            print(f'{self.use_space=}')

        def auto_actions(self, *action_names):
            return {act: getattr(self, act) for act in action_names}

        def actions(self):
            return self.auto_actions('back', 'forward', 'skip') | {
                'playpause': self.play_pause,
                'use-space': self.change_use_space,
            }

    app = App()

    with (Path(__file__).parent / 'secret.txt').open('r') as secret_file:
        secret = secret_file.read().strip()
    listener = WebSocketListener(
        "wss://clappy-play-pause.glitch.me/video-player",
        secret,
        app.actions(),
        bump_url='https://clappy-play-pause.glitch.me/bump'
    )
    listener.listen()


if __name__ == '__main__':
    fire.Fire()
