from datetime import datetime

from sim.config_models import SimConfig
from sim.operations.shift_calendar import ShiftCalendar

HOUR = 3600 * 1000


def _calendar(cfg: SimConfig) -> ShiftCalendar:
    return ShiftCalendar(cfg.shifts, datetime.fromisoformat(cfg.line.start_time))


def test_planned_time_is_shifts_minus_breaks(cfg: SimConfig) -> None:
    windows = _calendar(cfg).planned_windows(24 * HOUR)
    planned_h = sum(w.end_ms - w.start_ms for w in windows) / HOUR
    assert planned_h == 15.0  # 2 × 8 h minus 2 × 30 min
    assert len(windows) == 3  # 06:00-10:00, 10:30-18:00, 18:30-22:00 (14:00 merged)


def test_weekend_has_no_planned_time(cfg: SimConfig) -> None:
    saturday_ms = 5 * 24 * HOUR  # start is a Monday 05:30
    windows = _calendar(cfg).planned_windows(7 * 24 * HOUR)
    assert all(not (saturday_ms <= w.start_ms < saturday_ms + 2 * 24 * HOUR) for w in windows)


def test_response_factor_by_shift(cfg: SimConfig) -> None:
    cal = _calendar(cfg)
    assert cal.response_factor(int(3 * HOUR)) == 1.0    # 08:30, early shift
    assert cal.response_factor(int(11 * HOUR)) == 1.25  # 16:30, late shift
    assert cal.handovers(24 * HOUR) == [int(8.5 * HOUR)]  # 14:00
