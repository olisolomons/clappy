import time
from threading import Lock, Thread

import numpy as np

from clap_detector import ClapDetector
from constants import CHUNK
from settings import Settings, default_settings


class ClapSequenceBinary:
    def __init__(self, options, settings: Settings = default_settings, max_delay=1.5, min_delay=0.05):
        self.options = options
        self.sequence_length = int(np.ceil(np.log2(len(options) + 1)))
        self.sequence = []

        self.clap_detector = ClapDetector(self.on_clap, settings=settings)

        self.min_delay = min_delay
        self.max_delay = max_delay

        self.sequence_wait_thread = None
        self.lock = Lock()

    def on_clap(self, clap_frame_number):
        print('clap')
        fps = self.clap_detector.sample_rate / CHUNK
        clap_time = clap_frame_number / fps
        with self.lock:
            t = clap_time
            if self.sequence:
                if t - self.sequence[0] > self.max_delay * (self.sequence_length + 3):
                    self.sequence = []
                elif len(self.sequence) == 1 and t - self.sequence[-1] < self.min_delay:
                    return
            self.sequence.append(t)

            if len(self.sequence) == 2:
                wait_time = (self.sequence[1] - self.sequence[0]) * (self.sequence_length + 1)
                self.sequence_wait_thread = Thread(target=lambda: self.sequence_wait(wait_time))
                self.sequence_wait_thread.start()

    def sequence_wait(self, wait_time):
        time.sleep(wait_time)
        with self.lock:
            if len(self.sequence) >= 2:
                self.process_sequence(self.sequence)
                self.sequence = []

    def process_sequence(self, sequence):
        sequence = np.array(sequence)
        differences = sequence[1:] - sequence[:-1]
        command_sequence = differences[1:] / differences[:-1]

        command_bits = np.zeros(self.sequence_length, dtype=bool)
        command_bit_index = -1
        for command in command_sequence:
            command_bit_index += round(command)
            if not 0 <= command_bit_index < command_bits.shape[0]:
                return
            command_bits[command_bit_index] = True

        command_index = 0
        command_column_multiplier = 1
        for i, bit in enumerate(command_bits):
            command_index += bit * command_column_multiplier
            command_column_multiplier *= 2

        if command_index > 0:
            print(command_bits, command_index)
            command_function = self.options[command_index - 1]
            command_function()

    def listen(self, *, verbose=False):
        self.clap_detector.connect(verbose=verbose)
        self.clap_detector.listen(verbose=verbose)
