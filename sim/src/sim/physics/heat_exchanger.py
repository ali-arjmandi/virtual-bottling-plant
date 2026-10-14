"""HTST heat exchanger: first-order lag plus dead time on the outlet temperature (SIM-02).

Steady state rises with steam valve opening and steam pressure and falls with flow.
"""

from __future__ import annotations

import math
from collections import deque

STEAM_LIMIT_C = 140.0


class HeatExchanger:
    def __init__(
        self,
        tau_s: float,
        dead_time_s: float,
        tick_s: float,
        gain_c_per_pct: float,
        nominal_flow_lpm: float,
        initial_c: float,
    ) -> None:
        self.gain = gain_c_per_pct
        self.nominal_flow = nominal_flow_lpm
        self.outlet_c = initial_c
        self._alpha = 1.0 - math.exp(-tick_s / tau_s)
        delay_ticks = max(1, round(dead_time_s / tick_s))
        self._delay: deque[float] = deque([initial_c] * delay_ticks, maxlen=delay_ticks)

    def steady_state_c(
        self, inlet_c: float, valve_pct: float, pressure_ratio: float, flow_lpm: float
    ) -> float:
        rise = self.gain * valve_pct * pressure_ratio * (self.nominal_flow / max(flow_lpm, 1.0))
        return min(inlet_c + rise, STEAM_LIMIT_C)

    def step(self, target_c: float) -> float:
        delayed = self._delay[0]
        self._delay.append(target_c)
        self.outlet_c += (delayed - self.outlet_c) * self._alpha
        return self.outlet_c
