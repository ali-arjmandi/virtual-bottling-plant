"""Harness only: replays machine_status events so the summary can ask 'what was machine X doing
at time t'."""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

Event = dict[str, Any]


class StatusTimeline:
    def __init__(self, events: list[Event], machines: list[str]) -> None:
        self._times: dict[str, list[int]] = {m: [0] for m in machines}
        self._states: dict[str, list[tuple[str, str]]] = {m: [("stopped", "")] for m in machines}
        self._last_fault: dict[str, list[tuple[int, str]]] = {m: [] for m in machines}
        for e in events:
            if e["type"] != "machine_status" or e["machine"] not in self._times:
                continue
            m, cause = e["machine"], ",".join(e["data"]["cause"])
            self._times[m].append(e["t_ms"])
            self._states[m].append((e["data"]["status"], cause))
            if cause:
                self._last_fault[m].append((e["t_ms"], cause))

    def at(self, machine: str, t_ms: int) -> tuple[str, str]:
        """(status, cause) of the machine at t_ms."""
        i = bisect_right(self._times[machine], t_ms) - 1
        return self._states[machine][i]

    def last_cause(self, machine: str, t_ms: int, within_ms: int) -> str:
        """Most recent fault cause, if it started within the given window before t_ms."""
        history = self._last_fault[machine]
        i = bisect_right(history, (t_ms, "￿")) - 1
        if i >= 0 and t_ms - history[i][0] <= within_ms:
            return history[i][1]
        return ""
