"""C-501 cap hopper. The operator refills it after a random delay once it runs low; if they are
late, the capper runs out of caps (material shortage, SIM-22)."""

from __future__ import annotations

import numpy as np

from sim.config_models import CapperConfig
from sim.distributions import draw_duration_s
from sim.event_log import EventLog


class CapHopper:
    def __init__(self, cfg: CapperConfig, rng: np.random.Generator, log: EventLog) -> None:
        self.cfg = cfg
        self.caps = cfg.hopper_caps
        self._rng = rng
        self._log = log
        self._refill_due_ms: int | None = None

    @property
    def level_pct(self) -> float:
        return 100.0 * self.caps / self.cfg.hopper_caps

    @property
    def empty(self) -> bool:
        return self.caps <= 0

    def take_cap(self) -> bool:
        if self.caps <= 0:
            return False
        self.caps -= 1
        return True

    def step(self, t_ms: int, response_factor: float) -> bool:
        """Returns True when an empty hopper was just refilled."""
        if self._refill_due_ms is None and self.level_pct < self.cfg.hopper_refill_at_pct:
            delay_s = draw_duration_s(self.cfg.refill_delay, self._rng) * response_factor
            self._refill_due_ms = t_ms + int(delay_s * 1000)
        if self._refill_due_ms is not None and t_ms >= self._refill_due_ms:
            was_empty = self.empty
            self.caps = self.cfg.hopper_caps
            self._refill_due_ms = None
            self._log.emit(t_ms, "cap_hopper_refilled", "C501", was_empty=was_empty)
            return was_empty
        return False
