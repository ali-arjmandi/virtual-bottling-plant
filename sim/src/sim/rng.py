"""Seeded random streams. One named stream per subsystem, derived from a single master seed.

Streams are keyed by name (not by creation order), so adding a subsystem never changes the
numbers another subsystem sees.
"""

from __future__ import annotations

import zlib

import numpy as np


class RngFactory:
    def __init__(self, seed: int) -> None:
        self.seed = seed

    def stream(self, name: str) -> np.random.Generator:
        key = zlib.crc32(name.encode())
        return np.random.default_rng(np.random.SeedSequence(entropy=self.seed, spawn_key=(key,)))


class NoiseBuffer:
    """Standard-normal draws in batches. Per-sample numpy calls are too slow for every tick."""

    def __init__(self, rng: np.random.Generator, size: int = 4096) -> None:
        self._rng = rng
        self._size = size
        self._buf = rng.standard_normal(size)
        self._i = 0

    def next(self) -> float:
        if self._i >= self._size:
            self._buf = self._rng.standard_normal(self._size)
            self._i = 0
        value = float(self._buf[self._i])
        self._i += 1
        return value
