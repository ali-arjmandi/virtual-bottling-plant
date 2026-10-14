"""K-801 case packer. Collects bottles from CV4 into cases. Speed is in cases per minute."""

from __future__ import annotations

from sim.config_models import CasePackerConfig
from sim.flow.conveyor import Conveyor
from sim.machines.base_machine import Machine
from sim.machines.machine_status import Status, StatusTracker


class CasePacker(Machine):
    """Cycles are bottles; the PLC speed setpoint and reported speed are cases per minute."""

    def __init__(self, cfg: CasePackerConfig, status: StatusTracker, source: Conveyor) -> None:
        super().__init__("K801", cfg.max_speed_cpm * cfg.bottles_per_case, status)
        self.per_case = cfg.bottles_per_case
        self.source = source
        self.case_count = 0
        self._in_case = 0
        self.speed_sp_cpm = 0.0

    def step(self, dt_s: float, t_ms: int) -> None:
        self.speed_sp = self.speed_sp_cpm * self.per_case
        super().step(dt_s, t_ms)

    @property
    def speed_cpm(self) -> float:
        return self.speed / self.per_case

    def try_cycle(self) -> Status | None:
        if self.source.pop() is None:
            return Status.STARVED
        self._in_case += 1
        if self._in_case >= self.per_case:
            self._in_case = 0
            self.case_count += 1
        return None
