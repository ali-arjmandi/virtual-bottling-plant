"""L-601 labeler. Roll changes are count-based faults from the catalog (see fault_scheduler)."""

from __future__ import annotations

from sim.config_models import LabelerConfig
from sim.flow.conveyor import Conveyor
from sim.machines.base_machine import Machine
from sim.machines.machine_status import Status, StatusTracker


class Labeler(Machine):
    def __init__(
        self, cfg: LabelerConfig, status: StatusTracker, source: Conveyor, output: Conveyor
    ) -> None:
        super().__init__("L601", cfg.max_speed_bpm, status)
        self.source = source
        self.output = output

    def try_cycle(self) -> Status | None:
        if self.source.empty:
            return Status.STARVED
        if self.output.full:
            return Status.BLOCKED
        bottle = self.source.pop()
        assert bottle is not None
        self.output.push(bottle)
        return None
