import dataclasses
from typing import Callable, Any, Optional, Union, Generator, Iterable

import numpy as np
import pyaudio
from scipy.ndimage import gaussian_laplace, gaussian_filter1d

from constants import *
from settings import Settings, default_settings


class AudioStream:
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.it)

    def stop(self):
        try:
            self.it.send(True)
        except StopIteration:
            pass


class Clappy:
    def __init__(self, on_clap: Callable[[int], Any], settings: Settings = default_settings) -> None:
        self.audio: Optional[pyaudio.PyAudio] = None
        self.amplitudes_history: Optional[np.ndarray] = None
        self.sample_rate: Optional[int] = None
        self.device_info: Optional[dict] = None

        self.settings = settings
        self.auto_threshold = False
        if self.settings.threshold == 'auto':
            self.settings = dataclasses.replace(self.settings, threshold=0)
            self.auto_threshold = True

        self.on_clap = on_clap

    def copy_state(self, other: 'Clappy'):
        self.sample_rate = other.sample_rate
        self.amplitudes_history = np.zeros(self.seconds_to_buffer_size(AMPLITUDES_HISTORY_SECONDS))

    def seconds_to_buffer_size(self, seconds: float) -> int:
        return int(seconds * self.sample_rate / CHUNK)

    def connect(self, verbose: bool = False):
        self.audio = pyaudio.PyAudio()

        info = self.audio.get_host_api_info_by_index(0)
        device_infos = {
            i: device_info
            for i in range(info['deviceCount'])
            for device_info in (self.audio.get_device_info_by_host_api_device_index(0, i),)
            if device_info['maxInputChannels'] > 0
        }
        if verbose:
            for i, device_info in device_infos.items():
                print(f"Input Device id {i} - {device_info['name']}")

        self.device_info = next(
            device_info for device_info in device_infos.values() if device_info['name'] == 'default')
        self.sample_rate = int(self.device_info['defaultSampleRate'])
        if verbose:
            print(f'{self.sample_rate=}')

        self.amplitudes_history = np.zeros(self.seconds_to_buffer_size(AMPLITUDES_HISTORY_SECONDS))

    def stream(self) -> AudioStream:
        def stream_generator():
            stream = self.audio.open(format=FORMAT, channels=CHANNELS,
                                     rate=self.sample_rate, input=True,
                                     input_device_index=self.device_info['index'],
                                     frames_per_buffer=CHUNK)

            while True:
                chunk_bytes = stream.read(CHUNK, exception_on_overflow=False)
                chunk_array = np.frombuffer(chunk_bytes, dtype=np.int16)
                if (yield chunk_array):
                    break

            stream.stop_stream()
            stream.close()
            self.audio.terminate()

        return AudioStream(stream_generator())

    def listen(self, stream: Union[Generator[np.ndarray, bool, Any], Iterable[np.ndarray]] = None, *, verbose=False):
        stream = self.stream() if stream is None else stream
        frame_count = 0
        last_clap = 0

        try:
            while True:
                self.record_frame(stream)

                # find peaks
                gaussian_laplace_results = gaussian_laplace(
                    self.amplitudes_history,
                    sigma=self.settings.gaussian_laplace_sigma,
                    mode='nearest'
                )
                max_index = gaussian_laplace_results[last_clap:].argmax() + last_clap
                max_value = gaussian_laplace_results[max_index]
                if verbose:
                    print(f'{max_value=}')

                if max_value > self.settings.threshold and max_index < gaussian_laplace_results.size - 3:
                    self.on_clap(frame_count - gaussian_laplace_results.size + max_index)
                    last_clap = gaussian_laplace_results.size

                    self.amplitudes_history[:] = self.amplitudes_history[-1]

                    if self.auto_threshold:
                        new_threshold = max(int(max_value * AUTO_THRESHOLD_FRACTION), self.settings.threshold)
                        self.settings = dataclasses.replace(self.settings, threshold=new_threshold)

                frame_count += 1
                last_clap = max(last_clap - 1, 0)

        except KeyboardInterrupt:
            stream.stop()
        except StopIteration:
            pass

    def record_frame(self, stream: Generator[np.ndarray, bool, Any]):
        # get frequencies from microphone
        chunk_fft = np.fft.rfft(next(stream))
        # get relevant frequency datum
        gaussian_result = gaussian_filter1d(np.abs(chunk_fft), self.settings.freq_gaussian_sigma)
        # print(f"{gaussian_result[55]:10.0f}, {gaussian_result[250]:10.0f}")
        amplitude = gaussian_result[self.settings.clap_freq_index]
        # record in array
        self.amplitudes_history[:-1] = self.amplitudes_history[1:]
        self.amplitudes_history[-1] = amplitude


def clappy_test(settings: Settings = default_settings, *, verbose=False):
    clappy = Clappy(lambda: print("clap!"), settings=settings)
    clappy.connect(verbose=verbose)
    clappy.listen(verbose=verbose)
