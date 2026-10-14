"""Sim event log: one JSON object per line, used for determinism checks, the WS stream and
run summaries. Only physical/sim facts are logged, never control decisions."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any, TextIO

Event = dict[str, Any]


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 3)
    return value


class EventLog:
    def __init__(self, sink: TextIO | None = None, keep_last: int = 500) -> None:
        self._sink = sink
        self._recent: deque[Event] = deque(maxlen=keep_last)
        self._subscribers: list[asyncio.Queue[Event]] = []

    def emit(self, t_ms: int, type: str, machine: str | None = None, **data: Any) -> None:
        event: Event = {
            "t_ms": int(t_ms),
            "type": type,
            "machine": machine,
            "data": {k: _clean(v) for k, v in data.items()},
        }
        self._recent.append(event)
        if self._sink is not None:
            self._sink.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        for queue in self._subscribers:
            if not queue.full():
                queue.put_nowait(event)

    def recent(self, limit: int = 100) -> list[Event]:
        return list(self._recent)[-limit:]

    def clear(self) -> None:
        self._recent.clear()

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)
