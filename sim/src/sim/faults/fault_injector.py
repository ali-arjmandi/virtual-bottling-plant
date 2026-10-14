"""Starts and clears faults (random, scenario or API) and ends them after their duration."""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import simpy

from sim.config_models import FaultSpec
from sim.distributions import draw_duration_s
from sim.event_log import EventLog
from sim.faults.fault_catalog import FaultCatalog
from sim.faults.fault_target import FaultTarget

OPERATOR_KINDS = ("micro", "material")  # cleared by the operator, so slower on slower shifts


@dataclass
class ActiveFault:
    id: int
    machine: str
    spec: FaultSpec
    start_ms: int
    end_ms: int
    source: str
    params: dict[str, float] = field(default_factory=dict)


class FaultInjector:
    def __init__(
        self,
        env: simpy.Environment,
        log: EventLog,
        catalog: FaultCatalog,
        targets: dict[str, FaultTarget],
        rng: np.random.Generator,
        response_factor: Callable[[int], float],
    ) -> None:
        self.env = env
        self.log = log
        self.catalog = catalog
        self.targets = targets
        self.rng = rng
        self.response_factor = response_factor
        self.on_cleared: list[Callable[[ActiveFault], None]] = []
        self._active: dict[int, ActiveFault] = {}
        self._next_id = 1

    def active(self) -> list[ActiveFault]:
        return list(self._active.values())

    def is_active(self, machine: str, fault_type: str) -> bool:
        return any(f.machine == machine and f.spec.type == fault_type
                   for f in self._active.values())

    def start(
        self, machine: str, fault_type: str, duration_s: float | None = None,
        source: str = "random",
    ) -> ActiveFault:
        spec = self.catalog.get(machine, fault_type)
        if machine not in self.targets:
            raise KeyError(f"unknown machine {machine}")
        now = int(self.env.now)
        if duration_s is None:
            duration_s = draw_duration_s(spec.duration, self.rng)
            if spec.kind in OPERATOR_KINDS:
                duration_s *= self.response_factor(now)
        fault = ActiveFault(self._next_id, machine, spec, now, now + int(duration_s * 1000),
                            source, self._draw_params(spec))
        self._next_id += 1
        self._active[fault.id] = fault
        self.targets[machine].set_fault(spec, True, fault.params)
        self.log.emit(now, "fault_start", machine, id=fault.id, fault=spec.type,
                      kind=spec.kind, duration_s=duration_s, source=source, **fault.params)
        self.env.process(self._expire(fault))
        return fault

    def clear(self, fault_id: int) -> bool:
        fault = self._active.pop(fault_id, None)
        if fault is None:
            return False
        self.targets[fault.machine].set_fault(fault.spec, False, fault.params)
        self.log.emit(int(self.env.now), "fault_end", fault.machine, id=fault.id,
                      fault=fault.spec.type)
        for callback in self.on_cleared:
            callback(fault)
        return True

    def _expire(self, fault: ActiveFault) -> Generator[Any, Any, None]:
        yield self.env.timeout(max(0, fault.end_ms - fault.start_ms))
        self.clear(fault.id)

    def _draw_params(self, spec: FaultSpec) -> dict[str, float]:
        lo, hi = spec.effect.get("steam_factor_min"), spec.effect.get("steam_factor_max")
        if lo is not None and hi is not None:
            return {"steam_factor": float(self.rng.uniform(lo, hi))}
        return {}
