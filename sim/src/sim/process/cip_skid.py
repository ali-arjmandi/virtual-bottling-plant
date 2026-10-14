"""CIP skid: a packaged unit with its own sequence. It reports done after its cycle time."""

from __future__ import annotations

from sim.event_log import EventLog


class CipSkid:
    def __init__(self, duration_s: float, log: EventLog) -> None:
        self.duration_s = duration_s
        self.log = log
        self.run_cmd = False
        self.done = False
        self._elapsed_s = 0.0
        self._running = False

    @property
    def active(self) -> bool:
        return self._running and not self.done

    def step(self, dt_s: float, t_ms: int) -> None:
        if not self.run_cmd:
            if self._running:
                self.log.emit(t_ms, "cip_stopped", "T101", completed=self.done)
            self._running, self.done, self._elapsed_s = False, False, 0.0
            return
        if not self._running:
            self._running = True
            self.log.emit(t_ms, "cip_started", "T101")
        if self.done:
            return
        self._elapsed_s += dt_s
        if self._elapsed_s >= self.duration_s:
            self.done = True
            self.log.emit(t_ms, "cip_done", "T101")
