"""One simulator instance: SimPy environment, plant, register image and event log, plus the
controls the API and harness use (time, reset, faults, sensor overrides)."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, TextIO

import simpy

from sim.clock import SimClock
from sim.config_models import SimConfig
from sim.event_log import EventLog
from sim.io.register_image import RegisterImage
from sim.io.register_map import RegisterMap
from sim.plant import Plant
from sim.rng import RngFactory
from sim.sensors.sensor import OverrideMode, SensorOverride

MAX_TICKS_PER_STEP = 5000  # keeps the API responsive if the host falls behind


class SimRuntime:
    def __init__(
        self, cfg: SimConfig, reg_map: RegisterMap, seed: int, sink: TextIO | None = None
    ) -> None:
        self.cfg = cfg
        self.image = RegisterImage(reg_map)
        self.log = EventLog(sink)
        self.clock = SimClock(datetime.fromisoformat(cfg.line.start_time), cfg.line.tick_ms)
        self.seed = seed
        self.env = simpy.Environment()
        self.plant = self._build(seed)

    def _build(self, seed: int) -> Plant:
        self.seed = seed
        self.image.clear()
        self.log.clear()
        self.env = simpy.Environment()
        plant = Plant(self.env, self.cfg, self.image, self.log, RngFactory(seed))
        self.log.emit(0, "sim_reset", None, seed=seed)
        return plant

    def reset(self, seed: int, random_faults: bool = True) -> None:
        hooks = self.plant.after_tick
        self.plant = self._build(seed)
        self.plant.after_tick.extend(hooks)
        self.plant.scheduler.enabled = random_faults

    @property
    def t_ms(self) -> int:
        return int(self.env.now)

    def run_until(self, t_ms: int) -> None:
        """Processes every event up to and including t_ms."""
        if t_ms >= self.env.now:
            self.env.run(until=t_ms + 0.5)

    def run_for(self, ms: int) -> None:
        self.run_until(self.t_ms + ms)

    async def run_realtime(self) -> None:
        """Advances sim time at clock.speed × wall time until cancelled."""
        tick = self.cfg.line.tick_ms
        budget_ms = 0.0
        last = time.monotonic()
        while True:
            await asyncio.sleep(0.01)
            now = time.monotonic()
            if not self.clock.paused:
                budget_ms += (now - last) * 1000.0 * self.clock.speed
            last = now
            ticks = min(int(budget_ms // tick), MAX_TICKS_PER_STEP)
            if ticks:
                budget_ms -= ticks * tick
                self.run_until(self.t_ms - self.t_ms % tick + ticks * tick)

    # --- instructor controls ----------------------------------------------------------------

    def inject_fault(
        self, machine: str, fault_type: str, duration_s: float | None = None,
        params: dict[str, float] | None = None, source: str = "api",
    ) -> dict[str, Any]:
        params = params or {}
        if machine == "F401" and fault_type == "drift":
            nozzle = int(params.get("nozzle", self.cfg.line.filler.drift.nozzle))
            rate = float(params.get("rate_g_per_min", -0.5))
            self.plant.filler.weights.start_drift(nozzle, rate)
            self.log.emit(self.t_ms, "drift_start", machine, nozzle=nozzle,
                          rate_g_per_min=rate, source=source)
            return {"machine": machine, "type": fault_type, "nozzle": nozzle}
        fault = self.plant.injector.start(machine, fault_type, duration_s, source)
        return {"id": fault.id, "machine": machine, "type": fault_type,
                "durationS": (fault.end_ms - fault.start_ms) / 1000.0}

    def clear_fault(self, fault_id: int) -> bool:
        return self.plant.injector.clear(fault_id)

    def set_sensor_override(self, tag: str, mode: OverrideMode | None,
                            value: float | None = None) -> None:
        override = SensorOverride(mode, value) if mode else None
        self.plant.sensors.set_override(tag, override, self.t_ms)

    def disconnected_units(self) -> set[int]:
        return self.plant.sensors.disconnected_units()
