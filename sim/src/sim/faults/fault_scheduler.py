"""Random fault triggers (SIM-20..23). Each trigger clock runs on the target's age: running
seconds for time-based faults, cycles for count-based ones (e.g. a label roll)."""

from __future__ import annotations

from dataclasses import dataclass

from sim.config_models import FaultSpec, Weibull
from sim.distributions import draw_interval, is_count_based
from sim.faults.fault_injector import ActiveFault, FaultInjector
from sim.rng import RngFactory


@dataclass
class _Trigger:
    machine: str
    spec: FaultSpec
    next_at: float | None


class FaultScheduler:
    def __init__(self, injector: FaultInjector, rng_factory: RngFactory) -> None:
        self.injector = injector
        self.enabled = True  # False: only injected faults (tests, quiet demos)
        self._rngs = {
            f"{m}/{s.type}": rng_factory.stream(f"fault/{m}/{s.type}")
            for m in injector.catalog.machines() for s in injector.catalog.for_machine(m)
        }
        self._triggers: list[_Trigger] = []
        for machine in injector.catalog.machines():
            if machine not in injector.targets:
                continue
            for spec in injector.catalog.for_machine(machine):
                trigger = _Trigger(machine, spec, None)
                self._arm(trigger, first=True)
                self._triggers.append(trigger)
        injector.on_cleared.append(self._on_cleared)

    def remaining(self, machine: str, fault_type: str) -> float:
        """Age left until the next trigger (e.g. labels left on the roll)."""
        for t in self._triggers:
            if t.machine == machine and t.spec.type == fault_type:
                if t.next_at is None:
                    return 0.0
                return max(0.0, t.next_at - self._age(t))
        raise KeyError(f"unknown fault {machine}/{fault_type}")

    def step(self) -> None:
        if not self.enabled:
            return
        for t in self._triggers:
            if t.next_at is not None and self._age(t) >= t.next_at:
                t.next_at = None  # re-armed when the fault clears
                if not self.injector.is_active(t.machine, t.spec.type):
                    self.injector.start(t.machine, t.spec.type)

    def _on_cleared(self, fault: ActiveFault) -> None:
        for t in self._triggers:
            same = t.machine == fault.machine and t.spec.type == fault.spec.type
            if same and (t.next_at is None or is_count_based(t.spec.trigger)):
                self._arm(t)

    def _arm(self, t: _Trigger, first: bool = False) -> None:
        rng = self._rngs[f"{t.machine}/{t.spec.type}"]
        interval = draw_interval(t.spec.trigger, rng)
        if first and isinstance(t.spec.trigger, Weibull):
            interval *= float(rng.uniform())  # machines are not new: start part-way into life
        t.next_at = self._age(t) + interval

    def _age(self, t: _Trigger) -> float:
        return self.injector.targets[t.machine].fault_age(is_count_based(t.spec.trigger))
