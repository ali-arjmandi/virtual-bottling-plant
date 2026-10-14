"""T-101 mix tank: dosing valves, agitator, drain and transfer pump. Valves move only on PLC
commands; the tank reports what a real one would (level, Brix probe, flow meters)."""

from __future__ import annotations

from sim.config_models import MixTankConfig
from sim.physics.tank import Tank
from sim.quality.concentrate_supply import ConcentrateSupply


class MixTank:
    def __init__(self, cfg: MixTankConfig, supply: ConcentrateSupply, sugar_brix: float) -> None:
        self.cfg = cfg
        self.tank = Tank(cfg.capacity_l)
        self.supply = supply
        self.sugar_brix = sugar_brix
        self.mixedness = 1.0
        # PLC outputs
        self.water_open = self.conc_open = self.sugar_open = False
        self.agitator_on = self.pump_on = self.drain_open = False
        self.conc_select = 0
        # measured
        self.water_flow = self.conc_flow = self.sugar_flow = 0.0
        self.lot_no = 0

    @property
    def probe_brix(self) -> float:
        """The Brix probe sits low in the tank and reads high until the batch is mixed."""
        if self.tank.is_empty:
            return 0.0
        return self.tank.brix + (1.0 - self.mixedness) * self.cfg.stratification_bx

    def step(self, dt_s: float, t_ms: int, transfer_lpm: float) -> tuple[float, float]:
        """Advances one tick. Returns (litres, Brix) pumped to the pasteuriser."""
        minutes = dt_s / 60.0
        self.water_flow = self.cfg.water_flow_lpm if self.water_open else 0.0
        self.sugar_flow = self.cfg.sugar_flow_lpm if self.sugar_open else 0.0
        self.conc_flow = (
            self.cfg.conc_flow_lpm
            if self.conc_open and self.supply.is_known(self.conc_select)
            else 0.0
        )
        self._dose(self.water_flow * minutes, 0.0)
        self._dose(self.sugar_flow * minutes, self.sugar_brix)
        if self.conc_flow:
            volume = self.conc_flow * minutes
            self._dose(volume, self.supply.draw(self.conc_select, volume, t_ms))
        lot = self.supply.current_lot(self.conc_select, t_ms)
        self.lot_no = lot.lot_no if lot else 0

        if self.agitator_on and not self.tank.is_empty:
            self.mixedness += (1.0 - self.mixedness) * min(1.0, dt_s / self.cfg.mix_tau_s)
        if self.drain_open:
            self.tank.remove(self.cfg.drain_flow_lpm * minutes)
        if self.pump_on:
            return self.tank.remove(transfer_lpm * minutes)
        return 0.0, 0.0

    def receive_return(self, volume_l: float, brix: float) -> None:
        """Product diverted back by P-201."""
        self.tank.add(volume_l, brix)

    def _dose(self, volume_l: float, brix: float) -> None:
        if volume_l <= 0:
            return
        before = self.tank.volume_l
        accepted = self.tank.add(volume_l, brix)
        if accepted > 0:
            self.mixedness = self.mixedness * before / self.tank.volume_l
