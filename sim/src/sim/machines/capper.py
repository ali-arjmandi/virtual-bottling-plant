"""C-501 capper. Takes bottles from CV1, puts on a cap, passes them to CV2."""

from __future__ import annotations

from sim.config_models import CapperConfig
from sim.flow.conveyor import Conveyor
from sim.machines.base_machine import Machine
from sim.machines.cap_hopper import CapHopper
from sim.machines.machine_status import Status, StatusTracker
from sim.rng import NoiseBuffer


class Capper(Machine):
    def __init__(
        self,
        cfg: CapperConfig,
        status: StatusTracker,
        source: Conveyor,
        output: Conveyor,
        hopper: CapHopper,
        noise: NoiseBuffer,
    ) -> None:
        super().__init__("C501", cfg.max_speed_bpm, status)
        self.cfg = cfg
        self.source = source
        self.output = output
        self.hopper = hopper
        self.torque_nm = 0.0
        self._noise = noise

    def condition_causes(self) -> tuple[str, ...]:
        return ("caps_empty",) if self.hopper.empty else ()

    def try_cycle(self) -> Status | None:
        if self.source.empty:
            return Status.STARVED
        if self.output.full:
            return Status.BLOCKED
        bottle = self.source.pop()
        assert bottle is not None
        self.hopper.take_cap()
        self.output.push(bottle)
        self.torque_nm = self.cfg.torque_mean_nm + self.cfg.torque_sd_nm * self._noise.next()
        return None
