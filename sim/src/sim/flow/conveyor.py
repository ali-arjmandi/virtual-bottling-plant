"""Accumulation conveyor with finite capacity. Bottles keep their nozzle and fill weight so the
checkweigher can attribute them (SIM-11)."""

from __future__ import annotations

from collections import deque
from typing import NamedTuple


class Bottle(NamedTuple):
    nozzle: int
    weight_g: float


class Conveyor:
    def __init__(self, name: str, capacity: int) -> None:
        self.name = name
        self.capacity = capacity
        self._bottles: deque[Bottle] = deque()

    @property
    def fill(self) -> int:
        return len(self._bottles)

    @property
    def full(self) -> bool:
        return len(self._bottles) >= self.capacity

    @property
    def empty(self) -> bool:
        return not self._bottles

    def push(self, bottle: Bottle) -> bool:
        if self.full:
            return False
        self._bottles.append(bottle)
        return True

    def pop(self) -> Bottle | None:
        return self._bottles.popleft() if self._bottles else None
