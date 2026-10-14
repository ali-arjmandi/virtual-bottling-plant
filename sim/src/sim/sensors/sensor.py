"""One analog sensor: true value in, reported value out (noise, quantisation, faults).

SIM-40..42.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sim.config_models import SensorSpec
from sim.rng import NoiseBuffer

OverrideMode = Literal["stuck", "disconnect", "noise"]


@dataclass
class SensorOverride:
    mode: OverrideMode
    value: float | None = None  # stuck: fixed value (default: last reading); noise: extra sd


class Sensor:
    def __init__(self, name: str, spec: SensorSpec, noise: NoiseBuffer) -> None:
        self.name = name
        self.spec = spec
        self._noise = noise
        self.override: SensorOverride | None = None
        self.true_value = 0.0
        self.reported = 0.0

    def read(self, true_value: float) -> float:
        self.true_value = true_value
        mode = self.override.mode if self.override else None
        if mode in ("stuck", "disconnect"):
            return self.reported
        sd = self.spec.sd
        if mode == "noise" and self.override and self.override.value is not None:
            sd += self.override.value
        value = true_value + sd * self._noise.next() if sd else true_value
        self.reported = self._quantise(value)
        return self.reported

    def set_override(self, override: SensorOverride | None) -> None:
        if override and override.mode == "stuck" and override.value is not None:
            self.reported = override.value
        self.override = override

    def _quantise(self, value: float) -> float:
        step = self.spec.resolution
        return round(value / step) * step if step else value
