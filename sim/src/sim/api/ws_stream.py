"""WebSocket /ws: state snapshot at 2 Hz (wall time) plus every event as it happens."""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sim.api.state_snapshot import snapshot
from sim.runtime import SimRuntime

router = APIRouter()
STATE_PERIOD_S = 0.5


@router.websocket("/ws")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    runtime: SimRuntime = ws.app.state.runtime
    queue = runtime.log.subscribe()
    try:
        while True:
            await ws.send_json({"kind": "state", "state": snapshot(runtime)})
            deadline = asyncio.get_running_loop().time() + STATE_PERIOD_S
            while (remaining := deadline - asyncio.get_running_loop().time()) > 0:
                with contextlib.suppress(asyncio.TimeoutError):
                    event = await asyncio.wait_for(queue.get(), remaining)
                    await ws.send_json({"kind": "event", "event": event})
    except WebSocketDisconnect:
        pass
    finally:
        runtime.log.unsubscribe(queue)
