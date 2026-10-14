"""Polling helpers. Timeouts are real seconds; tests convert sim seconds with the sim speed."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(probe: Callable[[], T], timeout_s: float, what: str, interval_s: float = 0.2) -> T:
    """Returns the first truthy probe() result, or fails with the last value seen."""
    deadline = time.monotonic() + timeout_s
    last: T | None = None
    while time.monotonic() < deadline:
        last = probe()
        if last:
            return last
        time.sleep(interval_s)
    raise AssertionError(f"timed out after {timeout_s:.0f} s waiting for {what} (last: {last!r})")


def holds_for(probe: Callable[[], bool], duration_s: float, interval_s: float = 0.2) -> bool:
    """True if probe() stays truthy for the whole duration."""
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        if not probe():
            return False
        time.sleep(interval_s)
    return True
