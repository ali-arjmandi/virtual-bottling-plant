"""Harness only: the Phase 1 stand-in for the PLC. It talks to the sim only through the
register image, exactly as the PLC will over Modbus."""

from __future__ import annotations

from pathlib import Path

import yaml

from harness.stub_packaging import StubPackaging
from harness.stub_process import StubProcess
from sim.runtime import SimRuntime

PLAN_PATH = Path(__file__).with_name("production_plan.yaml")


class StubController:
    def __init__(self, runtime: SimRuntime, plan_path: Path = PLAN_PATH) -> None:
        plan = yaml.safe_load(plan_path.read_text())
        self.packaging = StubPackaging(runtime.image)
        self.process = StubProcess(runtime.image, plan, runtime.clock.start)

    def __call__(self, t_ms: int) -> None:
        self.packaging.step()
        self.process.step(t_ms)


def attach(runtime: SimRuntime) -> StubController:
    controller = StubController(runtime)
    runtime.plant.after_tick.append(controller)
    return controller
