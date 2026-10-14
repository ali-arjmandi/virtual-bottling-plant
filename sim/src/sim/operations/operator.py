"""The line operator: presses the local panel buttons (start at shift start and after breaks,
stop at breaks and shift end, reset after a stop cause is cleared; SIM-51)."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import numpy as np
import simpy

from sim.config_models import OperatorConfig
from sim.distributions import draw_duration_s
from sim.event_log import EventLog
from sim.faults.fault_injector import ActiveFault
from sim.operations.shift_calendar import ShiftCalendar

HORIZON_MS = 400 * 24 * 3600 * 1000  # schedule far ahead; runs are much shorter


@dataclass
class OperatorPanel:
    start: bool = False
    stop: bool = False
    reset: bool = False


class Operator:
    def __init__(
        self, env: simpy.Environment, cfg: OperatorConfig, calendar: ShiftCalendar,
        rng: np.random.Generator, log: EventLog,
    ) -> None:
        self.env = env
        self.cfg = cfg
        self.calendar = calendar
        self.rng = rng
        self.log = log
        self.panel = OperatorPanel()
        env.process(self._follow_calendar())
        if cfg.handover_stop_min > 0:
            env.process(self._shift_handovers())

    def on_fault_cleared(self, fault: ActiveFault) -> None:
        if fault.spec.stops_machine:
            self.env.process(self._press_after("reset", self._reset_delay_s()))

    def on_condition_cleared(self) -> None:
        """A non-fault stop cause (e.g. empty cap hopper) was fixed."""
        self.env.process(self._press_after("reset", self._reset_delay_s()))

    def _reset_delay_s(self) -> float:
        factor = self.calendar.response_factor(int(self.env.now))
        return draw_duration_s(self.cfg.reset_delay, self.rng) * factor

    def _follow_calendar(self) -> Generator[Any, Any, None]:
        for window in self.calendar.planned_windows(HORIZON_MS):
            start_ms = window.start_ms + int(draw_duration_s(self.cfg.start_delay, self.rng) * 1000)
            if start_ms > self.env.now:
                yield self.env.timeout(start_ms - self.env.now)
            yield from self._press("start")
            if window.end_ms > self.env.now:
                yield self.env.timeout(window.end_ms - self.env.now)
            yield from self._press("stop")

    def _shift_handovers(self) -> Generator[Any, Any, None]:
        half_ms = int(self.cfg.handover_stop_min * 60_000 / 2)
        for handover_ms in self.calendar.handovers(HORIZON_MS):
            if handover_ms - half_ms > self.env.now:
                yield self.env.timeout(handover_ms - half_ms - self.env.now)
            yield from self._press("stop")
            restart_ms = handover_ms + half_ms
            restart_ms += int(draw_duration_s(self.cfg.start_delay, self.rng) * 1000)
            yield self.env.timeout(max(0, restart_ms - self.env.now))
            yield from self._press("start")

    def _press_after(self, button: str, delay_s: float) -> Generator[Any, Any, None]:
        yield self.env.timeout(int(delay_s * 1000))
        yield from self._press(button)

    def _press(self, button: str) -> Generator[Any, Any, None]:
        setattr(self.panel, button, True)
        self.log.emit(int(self.env.now), "operator_button", None, button=button)
        yield self.env.timeout(int(self.cfg.button_pulse_s * 1000))
        setattr(self.panel, button, False)
