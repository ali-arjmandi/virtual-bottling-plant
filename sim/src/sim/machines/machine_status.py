"""Physical machine status as seen from the sim (not PackML; the PLC owns PackML).

Blocked and starved are debounced: a short wait between bottles is still 'producing'.
"""

from __future__ import annotations

from enum import StrEnum

from sim.event_log import EventLog


class Status(StrEnum):
    STOPPED = "stopped"      # run command off
    PRODUCING = "producing"
    STARVED = "starved"      # no input
    BLOCKED = "blocked"      # output full
    FAULTED = "faulted"      # a stopping fault is active

DEBOUNCED = (Status.STARVED, Status.BLOCKED)


class StatusTracker:
    def __init__(self, machine: str, log: EventLog, debounce_ms: int) -> None:
        self.machine = machine
        self.log = log
        self.debounce_ms = debounce_ms
        self.status = Status.STOPPED
        self.cause: tuple[str, ...] = ()
        self._pending: Status | None = None
        self._pending_since = 0

    def update(self, raw: Status, t_ms: int, cause: tuple[str, ...] = ()) -> None:
        if raw in DEBOUNCED and raw != self.status:
            if self._pending != raw:
                self._pending, self._pending_since = raw, t_ms
            if t_ms - self._pending_since < self.debounce_ms:
                return
        self._pending = None
        if raw != self.status or cause != self.cause:
            self.status, self.cause = raw, cause
            self.log.emit(t_ms, "machine_status", self.machine, status=raw.value,
                          cause=list(cause))
