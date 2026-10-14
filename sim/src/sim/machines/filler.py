"""F-401 rotary filler, 12 nozzles. Draws product from T-301 and fills bottles onto CV1."""

from __future__ import annotations

import numpy as np

from sim.config_models import FillerConfig
from sim.flow.conveyor import Bottle, Conveyor
from sim.machines.base_machine import Machine
from sim.machines.machine_status import Status, StatusTracker
from sim.process.buffer_tank import BufferTank
from sim.quality.fill_weight import FillWeightModel


class Filler(Machine):
    def __init__(
        self,
        cfg: FillerConfig,
        status: StatusTracker,
        supply: BufferTank,
        output: Conveyor,
        rng: np.random.Generator,
    ) -> None:
        super().__init__("F401", cfg.max_speed_bpm, status)
        self.cfg = cfg
        self.supply = supply
        self.output = output
        self.weights = FillWeightModel(cfg, rng)
        self.fill_target_g = 0.0  # PLC output (recipe)
        self._rng = rng
        self._efficiency = cfg.speed_efficiency.mean
        self._since_update_s = 0.0
        self._nozzle = 0
        self._underfill_left = 0
        self._was_producing = False

    def rate_factor(self) -> float:
        return self._efficiency

    def try_cycle(self) -> Status | None:
        if self.output.full:
            return Status.BLOCKED
        weight = self.weights.draw(self._nozzle, self.fill_target_g)
        if self._underfill_left > 0:
            self._underfill_left -= 1
            uf = self.cfg.restart_underfill
            weight += float(self._rng.normal(uf.mean_g, uf.sd_g))
        if not self.supply.draw_fill(weight / 1000.0):
            return Status.STARVED
        self.output.push(Bottle(self._nozzle + 1, weight))
        self._nozzle = (self._nozzle + 1) % self.cfg.nozzles
        return None

    def step(self, dt_s: float, t_ms: int) -> None:
        self.weights.step(dt_s, t_ms / 1000.0)
        self._since_update_s += dt_s
        eff = self.cfg.speed_efficiency
        if self._since_update_s >= eff.update_s:
            self._since_update_s = 0.0
            self._efficiency = min(1.0, float(self._rng.normal(eff.mean, eff.sd)))
        super().step(dt_s, t_ms)
        producing = self.status.status == Status.PRODUCING
        if producing and not self._was_producing:
            self._underfill_left = self.cfg.restart_underfill.bottles
        self._was_producing = producing
