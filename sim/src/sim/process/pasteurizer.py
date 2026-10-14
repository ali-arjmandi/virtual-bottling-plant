"""P-201 HTST pasteuriser: heats product from T-101 and sends it forward to T-301 or, with the
divert valve open, back to T-101."""

from __future__ import annotations

from sim.config_models import FaultSpec, PasteurizerConfig
from sim.physics.heat_exchanger import HeatExchanger


class Pasteurizer:
    def __init__(self, cfg: PasteurizerConfig, tick_s: float, inlet_c: float) -> None:
        self.cfg = cfg
        self.inlet_c = inlet_c
        self.hx = HeatExchanger(
            cfg.tau_s, cfg.dead_time_s, tick_s, cfg.gain_c_per_pct, cfg.transfer_flow_lpm,
            initial_c=cfg.ambient_c,
        )
        # PLC outputs
        self.steam_valve_pct = 0.0
        self.divert_cmd = False
        # state
        self.steam_factor = 1.0  # < 1 during a steam pressure drop
        self.flow_lpm = 0.0
        self.age_s = 0.0

    @property
    def outlet_c(self) -> float:
        return self.hx.outlet_c

    @property
    def steam_pressure_bar(self) -> float:
        return self.cfg.steam_pressure_bar * self.steam_factor

    @property
    def divert_open(self) -> bool:
        return self.divert_cmd

    # --- fault target ------------------------------------------------------------------------

    def fault_age(self, count_based: bool) -> float:
        return self.age_s

    def set_fault(self, spec: FaultSpec, active: bool, params: dict[str, float]) -> None:
        if "steam_factor" in params:
            self.steam_factor = params["steam_factor"] if active else 1.0

    def step(self, dt_s: float, volume_l: float) -> None:
        self.age_s += dt_s
        self.flow_lpm = volume_l / (dt_s / 60.0)
        hx_flow = max(self.flow_lpm, self.cfg.recirc_flow_lpm)
        valve = min(max(self.steam_valve_pct, 0.0), 100.0)
        target = self.hx.steady_state_c(self.inlet_c, valve, self.steam_factor, hx_flow)
        self.hx.step(target)
