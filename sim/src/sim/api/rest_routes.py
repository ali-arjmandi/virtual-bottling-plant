"""REST endpoints for the Instructor Station and the FAT suite (L0 network only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from sim.api.schemas import ClockRequest, FaultRequest, ResetRequest, SensorOverrideRequest
from sim.api.state_snapshot import snapshot
from sim.runtime import SimRuntime
from sim.scenarios.scenario_runner import load_scenario, run_scenario

router = APIRouter()


def _rt(request: Request) -> SimRuntime:
    runtime: SimRuntime = request.app.state.runtime
    return runtime


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/state")
def get_state(request: Request) -> dict[str, Any]:
    return snapshot(_rt(request))


@router.get("/events")
def get_events(request: Request, limit: int = 100) -> list[dict[str, Any]]:
    return _rt(request).log.recent(limit)


@router.post("/faults", status_code=201)
def post_fault(body: FaultRequest, request: Request) -> dict[str, Any]:
    try:
        return _rt(request).inject_fault(body.machine, body.type, body.duration_s, body.params)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/faults/{fault_id}", status_code=204)
def delete_fault(fault_id: int, request: Request) -> None:
    if not _rt(request).clear_fault(fault_id):
        raise HTTPException(404, f"no active fault {fault_id}")


@router.post("/sensors/{tag}/override", status_code=204)
def post_sensor_override(tag: str, body: SensorOverrideRequest, request: Request) -> None:
    try:
        _rt(request).set_sensor_override(tag, body.mode, body.value)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/sensors/{tag}/override", status_code=204)
def delete_sensor_override(tag: str, request: Request) -> None:
    try:
        _rt(request).set_sensor_override(tag, None)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/clock")
def post_clock(body: ClockRequest, request: Request) -> dict[str, Any]:
    clock = _rt(request).clock
    if body.speed is not None:
        clock.set_speed(float(body.speed))
    if body.paused is not None:
        clock.paused = body.paused
    return {"speed": clock.speed, "paused": clock.paused}


@router.post("/reset")
def post_reset(body: ResetRequest, request: Request) -> dict[str, Any]:
    _rt(request).reset(body.seed)
    return {"seed": body.seed}


@router.post("/scenarios/{name}/run", status_code=202)
def post_scenario(name: str, request: Request) -> dict[str, Any]:
    try:
        scenario = load_scenario(name)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    run_scenario(_rt(request), scenario)
    return {"scenario": scenario.name, "steps": len(scenario.steps)}
