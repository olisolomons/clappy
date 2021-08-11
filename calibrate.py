import json
from dataclasses import dataclass
from queue import Queue, Empty
from threading import Thread
from typing import Tuple, Callable, Any, Optional

import numpy as np

from clappy import Clappy
from settings import Settings


def input_choice(choices: dict[str, Tuple[str, Callable[[], Any]]]):
    question = f'Choose from:\n' + '\n'.join(f'{k}: {desc}' for k, (desc, action) in choices.items()) + '\n'
    while True:
        inp = input(question)
        if inp in choices:
            return choices[inp][1]()
        else:
            print(f'Bad input \'{inp}\': not one of the choices')


class Calibrator:
    def __init__(self, restore_state_bytes: Optional[bytes] = None):
        def raise_error():
            raise RuntimeError()

        self.capturing_clappy = Clappy(raise_error)
        self.labelled_chunks: list[Tuple[list[np.ndarray], bool]] = []

        if restore_state_bytes is not None:
            restore_state = json.loads(restore_state_bytes.decode('utf-8'))
            self.labelled_chunks = [
                ([np.array(chunk, dtype=np.int16) for chunk in chunks], label)
                for chunks, label in restore_state['labelled_chunks']
            ]
            self.capturing_clappy.sample_rate = restore_state['sample_rate']

    def capture(self) -> None:
        self.capturing_clappy.connect()
        stream = self.capturing_clappy.stream()
        choices = {
            'y': ('yes, I just clapped', lambda: True),
            'n': ('no, I didn\'t clap', lambda: False),
            'exit': ('exit', lambda: 'exit')
        }

        input_queue = Queue()

        def capturing_worker():
            working_chunks = []
            for chunk in stream:
                working_chunks.append(chunk)
                try:
                    command = input_queue.get(block=False)
                    if command == 'exit':
                        break
                    else:
                        self.labelled_chunks.append((working_chunks, command))
                        working_chunks = []
                except Empty:
                    pass

        capturing_thread = Thread(target=capturing_worker)
        capturing_thread.start()

        while True:
            try:
                command = input_choice(choices)
            except KeyboardInterrupt:
                command = 'exit'
            print(f'{command=}')
            input_queue.put(command)

            if command == 'exit':
                break

        capturing_thread.join()

    def score_settings(self, settings: Settings, verbose: bool = False) -> float:
        if len(self.labelled_chunks) == 0:
            raise ValueError('Cannot call score_settings before labelling some chunks')

        @dataclass
        class ClappyReport:
            clapped = False

            def reset(self):
                self.clapped = False

            def report_clap(self):
                self.clapped = True

        clappy_report = ClappyReport()

        clappy = Clappy(clappy_report.report_clap, settings=settings)
        clappy.copy_state(self.capturing_clappy)

        correct_count = 0

        # copy in case threading is used
        labelled_chunks_copy = list(self.labelled_chunks)

        for chunks, contains_clap in labelled_chunks_copy:
            clappy.listen(iter(chunks))
            if verbose:
                print(f'{clappy_report.clapped=}; {contains_clap=}')

            if clappy_report.clapped == contains_clap:
                correct_count += 1

            clappy_report.reset()

        return correct_count / len(labelled_chunks_copy)

    def state_to_bytes(self) -> bytes:
        json_ready_state = {
            'labelled_chunks': [
                ([chunk.tolist() for chunk in chunks], label)
                for chunks, label in self.labelled_chunks
            ],
            'sample_rate': self.capturing_clappy.sample_rate
        }
        return json.dumps(json_ready_state).encode('utf-8')

    def calibrate(self, *, depth: int, grid_size: int = 4) -> Settings:
        maximums = max_settings.to_array()
        minimums = np.ones_like(maximums)

        winner1 = None
        for i in range(depth):
            grid = np.stack(np.meshgrid(*[
                np.linspace(min_val, max_val, num=grid_size, endpoint=True).astype(np.int32)
                for min_val, max_val in zip(minimums, maximums)
            ]), axis=maximums.size)

            fitness = np.empty(grid.shape[:-1])

            # winner = max(np.ndindex(grid.shape[:-1]), key=score_settings_index)
            for settings_index in np.ndindex(grid.shape[:-1]):
                settings = Settings.from_array(grid[settings_index])
                fitness[settings_index] = self.score_settings(settings)

            if fitness.min() == fitness.max():
                return Settings.from_array(((maximums + minimums) / 2).astype(np.int32))

            winner1, winner2 = [
                grid[tuple(winner)]
                for winner in np.stack(
                    np.unravel_index(
                        np.argpartition(fitness, -2, axis=None)[-2:], fitness.shape
                    )
                ).transpose()
            ]

            minimums = np.minimum(winner1, winner2)
            maximums = np.maximum(winner1, winner2)

        return Settings.from_array(winner1)


def calibrate():
    calib = Calibrator()
    calib.capture()
    print(calib.calibrate(depth=4))