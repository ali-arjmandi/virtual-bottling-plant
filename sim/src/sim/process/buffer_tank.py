"""T-301 buffer tank between process and packaging."""

from __future__ import annotations

from sim.config_models import BufferTankConfig
from sim.physics.tank import Tank


class BufferTank:
    def __init__(self, cfg: BufferTankConfig) -> None:
        self.cfg = cfg
        self.tank = Tank(cfg.capacity_l)
        self.drain_open = False

    @property
    def suction_low(self) -> bool:
        return self.tank.level_pct < self.cfg.suction_low_pct

    def receive(self, volume_l: float, brix: float) -> None:
        self.tank.add(volume_l, brix)

    def draw_fill(self, volume_l: float) -> bool:
        """Filler draws one bottle. Fails (starved) when the suction is uncovered."""
        if self.suction_low:
            return False
        self.tank.remove(volume_l)
        return True

    def step(self, dt_s: float) -> None:
        if self.drain_open:
            self.tank.remove(self.cfg.drain_flow_lpm * dt_s / 60.0)
