#!/usr/bin/python3
import dataclasses
import time
from threading import Thread

import settings
from clappy_sequence import ClappySequence
import subprocess
import fire


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


def clappy(verbose=False, threshold='auto'):
    print('Listening for claps!')
    use_settings = dataclasses.replace(settings.default_settings, threshold=threshold)

    clappy_sequence = ClappySequence([
        lambda key=key: (print(key), press('/dev/input/event3', key))
        for key in ['KEY_PLAYPAUSE', 'KEY_LEFT', 'KEY_RIGHT']
    ], settings=use_settings)

    if threshold == 'auto':
        def turn_off_auto_delayed():
            time.sleep(10)
            clappy_sequence.clappy.auto_threshold = False
            threshold = clappy_sequence.clappy.settings.threshold
            print(f'Auto threshold tuning turned off, {threshold=}')

        thread = Thread(target=turn_off_auto_delayed)
        thread.start()

    clappy_sequence.listen(verbose=verbose)


if __name__ == '__main__':
    fire.Fire(clappy)
