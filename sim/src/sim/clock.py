"""Sim time. SimPy runs in integer milliseconds; this maps them to calendar time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

ALLOWED_SPEEDS = (1.0, 10.0, 60.0)


@dataclass
class SimClock:
    start: datetime
    tick_ms: int
    speed: float = 1.0
    paused: bool = False

    def to_datetime(self, t_ms: float) -> datetime:
        return self.start + timedelta(milliseconds=t_ms)

    def set_speed(self, speed: float) -> None:
        if speed not in ALLOWED_SPEEDS:
            raise ValueError(f"speed must be one of {ALLOWED_SPEEDS}")
        self.speed = speed
