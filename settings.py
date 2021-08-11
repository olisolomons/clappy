import dataclasses
from dataclasses import dataclass

import numpy as np
from constants import *


@dataclass(frozen=True)
class Settings:
    clap_freq_index: int
    threshold: int
    gaussian_laplace_sigma: int
    freq_gaussian_sigma: int

    @staticmethod
    def from_array(arr):
        return Settings(**{
            field.name: x
            for field, x in zip(dataclasses.fields(Settings), arr)
        })

    def to_array(self):
        return np.array([getattr(self, field.name) for field in dataclasses.fields(Settings)])


default_settings = Settings(
    clap_freq_index=1655,
    threshold=7750,
    gaussian_laplace_sigma=1,
    freq_gaussian_sigma=117
)
max_settings = Settings(
    clap_freq_index=CHUNK // 2 - 1,
    threshold=1000,
    gaussian_laplace_sigma=30,
    freq_gaussian_sigma=300
)
