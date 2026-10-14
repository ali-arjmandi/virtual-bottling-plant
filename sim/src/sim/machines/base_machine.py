"""Common behaviour of packaging machines (SIM-10, SIM-12).

A machine cycles only while the PLC run command is on, no stopping fault is active, it has
input and its output has room. It exposes causes (faults, empty, full); it never decides state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sim.config_models import FaultSpec
from sim.machines.machine_status import Status, StatusTracker

SPEED_SMOOTHING = 0.05  # EMA factor per tick for the reported speed


class Machine(ABC):
    def __init__(self, name: str, max_speed: float, status: StatusTracker) -> None:
        self.name = name
        self.max_speed = max_speed  # cycles per minute
        self.status = status
        # PLC outputs
        self.run_cmd = False
        self.speed_sp = 0.0
        # state
        self.active_faults: dict[str, FaultSpec] = {}
        self.cycles = 0
        self.running_s = 0.0
        self.speed = 0.0
        self._progress = 0.0

    # --- hooks for subclasses ---------------------------------------------------------------

    @abstractmethod
    def try_cycle(self) -> Status | None:
        """Does one cycle. Returns None on success, or STARVED / BLOCKED."""

    def rate_factor(self) -> float:
        return 1.0

    def condition_causes(self) -> tuple[str, ...]:
        """Stopping causes from physical state (e.g. an empty cap hopper)."""
        return ()

    # --- faults -----------------------------------------------------------------------------

    def fault_age(self, count_based: bool) -> float:
        """Clock that fault triggers run on: cycles, or seconds of producing."""
        return float(self.cycles) if count_based else self.running_s

    def set_fault(self, spec: FaultSpec, active: bool, params: dict[str, float]) -> None:
        if active:
            self.active_faults[spec.type] = spec
        else:
            self.active_faults.pop(spec.type, None)

    def fault_signal_active(self, signal: str) -> bool:
        return any(f.signal == signal for f in self.active_faults.values())

    def stop_causes(self) -> tuple[str, ...]:
        faults = tuple(t for t, f in self.active_faults.items() if f.stops_machine)
        return faults + self.condition_causes()

    # --- tick -------------------------------------------------------------------------------

    def step(self, dt_s: float, t_ms: int) -> None:
        causes = self.stop_causes()
        moved = 0
        if causes:  # a jammed machine is jammed whether or not the PLC still commands it
            raw = Status.FAULTED
        elif not self.run_cmd:
            raw, self._progress = Status.STOPPED, 0.0
        else:
            raw = Status.PRODUCING
            rate = min(max(self.speed_sp, 0.0), self.max_speed) * self.rate_factor()
            self._progress += rate / 60.0 * dt_s
            while self._progress >= 1.0:
                result = self.try_cycle()
                if result is not None:
                    raw, self._progress = result, 1.0
                    break
                self._progress -= 1.0
                moved += 1
            if moved:
                raw = Status.PRODUCING
            if raw == Status.PRODUCING:
                self.running_s += dt_s
        self.cycles += moved
        self.speed += (moved / dt_s * 60.0 - self.speed) * SPEED_SMOOTHING
        self.status.update(raw, t_ms, causes if raw == Status.FAULTED else ())

    @property
    def running(self) -> bool:
        """Motor-running feedback: commanded on and not stopped by a fault."""
        return self.run_cmd and not self.stop_causes()
