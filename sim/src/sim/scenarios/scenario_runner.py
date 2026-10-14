"""Plays a scenario file (sim/scenarios/<name>.yaml): faults and sensor overrides at fixed sim
times after start, so a demo recording is the same every time (SIM-64)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from sim.runtime import SimRuntime

SCENARIO_DIR = Path(__file__).resolve().parents[3] / "scenarios"


class ScenarioStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at_s: float
    action: Literal["fault", "drift", "sensor", "sensor_clear"]
    machine: str | None = None
    type: str | None = None
    duration_s: float | None = None
    nozzle: int | None = None
    rate_g_per_min: float | None = None
    tag: str | None = None
    mode: Literal["stuck", "disconnect", "noise"] | None = None
    value: float | None = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str = ""
    steps: list[ScenarioStep]


def load_scenario(name: str, directory: Path = SCENARIO_DIR) -> Scenario:
    path = directory / f"{name}.yaml"
    if not path.is_file() or path.parent != directory:
        raise KeyError(f"unknown scenario {name}")
    return Scenario.model_validate(yaml.safe_load(path.read_text()))


def run_scenario(runtime: SimRuntime, scenario: Scenario) -> None:
    runtime.log.emit(runtime.t_ms, "scenario_start", None, name=scenario.name)
    runtime.env.process(_play(runtime, scenario, runtime.t_ms))


def _play(runtime: SimRuntime, scenario: Scenario, start_ms: int) -> Generator[Any, Any, None]:
    for step in sorted(scenario.steps, key=lambda s: s.at_s):
        due = start_ms + int(step.at_s * 1000)
        if due > runtime.env.now:
            yield runtime.env.timeout(due - runtime.env.now)
        _apply(runtime, step)
    runtime.log.emit(runtime.t_ms, "scenario_end", None, name=scenario.name)


def _apply(runtime: SimRuntime, step: ScenarioStep) -> None:
    if step.action == "fault" and step.machine and step.type:
        runtime.inject_fault(step.machine, step.type, step.duration_s, source="scenario")
    elif step.action == "drift" and step.nozzle:
        params = {"nozzle": float(step.nozzle), "rate_g_per_min": step.rate_g_per_min or -1.0}
        runtime.inject_fault("F401", "drift", params=params, source="scenario")
    elif step.action == "sensor" and step.tag and step.mode:
        runtime.set_sensor_override(step.tag, step.mode, step.value)
    elif step.action == "sensor_clear" and step.tag:
        runtime.set_sensor_override(step.tag, None)
