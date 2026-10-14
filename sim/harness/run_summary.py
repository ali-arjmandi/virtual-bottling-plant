"""Harness only: OEE estimate and downtime Pareto from a run's event log, used to tune the
fault parameters. The real OEE is the MES's job (Phase 5).

Losses are booked on the root cause: a filler blocked by a jammed capper is a capper jam.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from harness.status_timeline import Event, StatusTimeline
from sim.operations.shift_calendar import Window

DOWNSTREAM = ["C501", "L601", "Q701", "K801"]
SAMPLE_MS = 1000
RECENT_FAULT_MS = 10 * 60_000
IDEAL_BPM = 120.0
PROCESS_TAIL_MS = 30 * 60_000


def _changeover_windows(events: list[Event]) -> list[Window]:
    """From CIP start until the filler produces again."""
    windows: list[Window] = []
    start: int | None = None
    for e in events:
        if e["type"] == "cip_started":
            start = e["t_ms"]
        elif (start is not None and e["type"] == "machine_status" and e["machine"] == "F401"
              and e["data"]["status"] == "producing"):
            windows.append(Window(start, e["t_ms"]))
            start = None
    return windows


def _process_fault_windows(events: list[Event]) -> list[tuple[Window, str]]:
    """P-201 faults plus a recovery tail, since the buffer needs time to refill."""
    starts = {e["data"]["id"]: e for e in events
              if e["type"] == "fault_start" and e["machine"] == "P201"}
    out: list[tuple[Window, str]] = []
    for e in events:
        if e["type"] == "fault_end" and e["data"]["id"] in starts:
            out.append((Window(starts[e["data"]["id"]]["t_ms"], e["t_ms"] + PROCESS_TAIL_MS),
                        f"P201 {e['data']['fault']}"))
    return out


def _reason(
    tl: StatusTimeline, t: int, changeovers: list[Window],
    process_faults: list[tuple[Window, str]],
) -> str | None:
    status, cause = tl.at("F401", t)
    if status == "producing":
        return None
    if any(w.start_ms <= t < w.end_ms for w in changeovers):
        return "Changeover (drain + CIP + first batch)"
    if status == "faulted":
        return f"F401 {cause}"
    if status == "starved":
        for w, name in process_faults:
            if w.start_ms <= t < w.end_ms:
                return name
        return "Process supply (T-301 empty)"
    if status == "stopped":
        return "Line stopped (start-up / handover)"
    for machine in DOWNSTREAM:  # blocked: find the root cause downstream
        d_status, d_cause = tl.at(machine, t)
        if d_status == "faulted":
            return f"{machine} {d_cause}"
        if d_status == "stopped":
            last = tl.last_cause(machine, t, RECENT_FAULT_MS)
            return f"{machine} {last}" if last else f"{machine} stopped"
        if d_status != "blocked":
            return "F401 blocked (other)"
    return "F401 blocked (other)"


def summarize(
    events: list[Event], windows: list[Window], end_ms: int, counts: dict[str, int]
) -> dict[str, Any]:
    tl = StatusTimeline(events, ["F401", *DOWNSTREAM])
    changeovers = _changeover_windows(events)
    process_faults = _process_fault_windows(events)
    losses: Counter[str] = Counter()  # seconds
    planned_s = run_s = 0.0
    for w in windows:
        for t in range(max(w.start_ms, 0), min(w.end_ms, end_ms), SAMPLE_MS):
            planned_s += SAMPLE_MS / 1000
            reason = _reason(tl, t, changeovers, process_faults)
            if reason is None:
                run_s += SAMPLE_MS / 1000
            else:
                losses[reason] += SAMPLE_MS // 1000

    filled = counts["F401"]
    good = counts["Q701"] - counts["Q701_rejects"]
    availability = run_s / planned_s if planned_s else 0.0
    performance = filled / (IDEAL_BPM / 60 * run_s) if run_s else 0.0
    quality = good / filled if filled else 0.0
    lost_s = sum(losses.values())
    return {
        "planned_h": round(planned_s / 3600, 2),
        "run_h": round(run_s / 3600, 2),
        "oee": round(availability * performance * quality, 4),
        "availability": round(availability, 4),
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "counts": counts,
        "pareto": [
            {"reason": r, "minutes": round(s / 60, 1), "share": round(s / lost_s, 3)}
            for r, s in losses.most_common()
        ],
    }
