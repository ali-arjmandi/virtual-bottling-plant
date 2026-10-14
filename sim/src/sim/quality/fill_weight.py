"""Fill weight per nozzle: normal around target + a fixed nozzle offset + slow drift (SIM-30/31)."""

from __future__ import annotations

import numpy as np

from sim.config_models import FillerConfig
from sim.rng import NoiseBuffer


class FillWeightModel:
    def __init__(self, cfg: FillerConfig, rng: np.random.Generator) -> None:
        self.sd = cfg.fill_sd_g
        self.offsets = [float(x) for x in rng.normal(0.0, cfg.nozzle_offset_sd_g, cfg.nozzles)]
        self.drift_g = [0.0] * cfg.nozzles
        self.drift_rate_g_per_s = [0.0] * cfg.nozzles
        self._noise = NoiseBuffer(rng)
        self._configured_drift = cfg.drift
        self._drift_start_s: float | None = cfg.drift.start_after_h * 3600.0

    def start_drift(self, nozzle: int, rate_g_per_min: float) -> None:
        """nozzle is 1-based, as on the machine."""
        self.drift_rate_g_per_s[nozzle - 1] = rate_g_per_min / 60.0

    def reset_drift(self, nozzle: int) -> None:
        self.drift_rate_g_per_s[nozzle - 1] = 0.0
        self.drift_g[nozzle - 1] = 0.0

    def step(self, dt_s: float, sim_s: float) -> None:
        if self._drift_start_s is not None and sim_s >= self._drift_start_s:
            cfg = self._configured_drift
            self.start_drift(cfg.nozzle, cfg.rate_g_per_h / 60.0)
            self._drift_start_s = None
        for i, rate in enumerate(self.drift_rate_g_per_s):
            if rate:
                self.drift_g[i] += rate * dt_s

    def draw(self, nozzle_index: int, target_g: float) -> float:
        return (
            target_g
            + self.offsets[nozzle_index]
            + self.drift_g[nozzle_index]
            + self.sd * self._noise.next()
        )
