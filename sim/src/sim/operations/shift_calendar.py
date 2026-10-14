"""Shift calendar: planned production windows, breaks and the shift's response factor (SIM-50)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sim.config_models import ShiftConfig, ShiftsConfig


@dataclass(frozen=True)
class Window:
    start_ms: int
    end_ms: int


def _at(day: datetime, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(day.date(), time(h, m), tzinfo=day.tzinfo)


class ShiftCalendar:
    def __init__(self, cfg: ShiftsConfig, start: datetime) -> None:
        self.cfg = cfg
        self.start = start

    def _ms(self, moment: datetime) -> int:
        return int((moment - self.start).total_seconds() * 1000)

    def planned_windows(self, until_ms: int) -> list[Window]:
        """Production time (shifts minus breaks), merged across shift changes."""
        windows: list[Window] = []
        day = self.start.replace(hour=0, minute=0, second=0, microsecond=0)
        while self._ms(day) < until_ms:
            if day.weekday() in self.cfg.working_days:
                for shift in self.cfg.shifts:
                    windows.extend(self._shift_windows(day, shift))
            day += timedelta(days=1)
        return self._merge([w for w in windows if w.end_ms > 0 and w.start_ms < until_ms])

    def handovers(self, until_ms: int) -> list[int]:
        """Times where one shift ends and the next starts straight away."""
        times: list[int] = []
        day = self.start.replace(hour=0, minute=0, second=0, microsecond=0)
        starts = {s.start for s in self.cfg.shifts}
        while self._ms(day) < until_ms:
            if day.weekday() in self.cfg.working_days:
                times += [self._ms(_at(day, s.end)) for s in self.cfg.shifts if s.end in starts]
            day += timedelta(days=1)
        return sorted(t for t in times if 0 < t < until_ms)

    def shift_at(self, t_ms: int) -> ShiftConfig | None:
        now = self.start + timedelta(milliseconds=t_ms)
        if now.weekday() not in self.cfg.working_days:
            return None
        for shift in self.cfg.shifts:
            if _at(now, shift.start) <= now < _at(now, shift.end):
                return shift
        return None

    def response_factor(self, t_ms: int) -> float:
        shift = self.shift_at(t_ms)
        return shift.response_factor if shift else 1.0

    def _shift_windows(self, day: datetime, shift: ShiftConfig) -> list[Window]:
        cursor, end = _at(day, shift.start), _at(day, shift.end)
        out: list[Window] = []
        for brk in sorted(shift.breaks, key=lambda b: b.start):
            b_start = _at(day, brk.start)
            out.append(Window(self._ms(cursor), self._ms(b_start)))
            cursor = b_start + timedelta(minutes=brk.minutes)
        out.append(Window(self._ms(cursor), self._ms(end)))
        return out

    @staticmethod
    def _merge(windows: list[Window]) -> list[Window]:
        merged: list[Window] = []
        for w in sorted(windows, key=lambda w: w.start_ms):
            if merged and w.start_ms <= merged[-1].end_ms:
                merged[-1] = Window(merged[-1].start_ms, max(merged[-1].end_ms, w.end_ms))
            else:
                merged.append(w)
        return merged
