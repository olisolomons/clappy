import dataclasses
from dataclasses import dataclass

import numpy as np
from constants import *


@dataclass(frozen=True)
class Settings:
    clap_freq_index: int
    threshold: float
    gaussian_laplace_sigma: float
    freq_gaussian_sigma: float

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
    gaussian_laplace_sigma=0.7,
    freq_gaussian_sigma=117
)
max_settings = Settings(
    clap_freq_index=CHUNK // 2 - 1,
    threshold=1000,
    gaussian_laplace_sigma=30,
    freq_gaussian_sigma=300
)
