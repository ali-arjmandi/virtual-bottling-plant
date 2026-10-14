"""Q-701 checkweigher. Weighs every bottle, rejects light ones and publishes per-nozzle
subgroup statistics (mean, range, n = subgroup_size), like a real checkweigher does."""

from __future__ import annotations

from dataclasses import dataclass, field

from sim.config_models import CheckweigherConfig
from sim.flow.conveyor import Conveyor
from sim.machines.base_machine import Machine
from sim.machines.machine_status import Status, StatusTracker
from sim.rng import NoiseBuffer

SCALE_SD_G = 0.2


@dataclass
class Subgroup:
    seq: int = 0
    mean_g: float = 0.0
    range_g: float = 0.0
    pending: list[float] = field(default_factory=list)


class Checkweigher(Machine):
    def __init__(
        self,
        cfg: CheckweigherConfig,
        nozzles: int,
        status: StatusTracker,
        source: Conveyor,
        output: Conveyor,
        noise: NoiseBuffer,
    ) -> None:
        super().__init__("Q701", cfg.max_speed_bpm, status)
        self.cfg = cfg
        self.source = source
        self.output = output
        self.reject_limit_g = 0.0  # PLC output
        self.reject_count = 0
        self.last_weight_g = 0.0
        self.subgroups = [Subgroup() for _ in range(nozzles)]
        self._noise = noise

    def try_cycle(self) -> Status | None:
        if self.source.empty:
            return Status.STARVED
        if self.output.full:
            return Status.BLOCKED
        bottle = self.source.pop()
        assert bottle is not None
        weight = bottle.weight_g + SCALE_SD_G * self._noise.next()
        self.last_weight_g = weight
        self._record(bottle.nozzle, weight)
        if weight < self.reject_limit_g:
            self.reject_count += 1
        else:
            self.output.push(bottle)
        return None

    def _record(self, nozzle: int, weight: float) -> None:
        group = self.subgroups[nozzle - 1]
        group.pending.append(weight)
        if len(group.pending) >= self.cfg.subgroup_size:
            group.mean_g = sum(group.pending) / len(group.pending)
            group.range_g = max(group.pending) - min(group.pending)
            group.seq = (group.seq + 1) % 0x10000
            group.pending.clear()
