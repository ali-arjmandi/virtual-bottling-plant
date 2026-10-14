from __future__ import annotations

from pathlib import Path

import pytest

from harness.stub_controller import StubController, attach
from sim.config_models import SimConfig, load_config
from sim.io.register_map import RegisterMap
from sim.runtime import SimRuntime

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
FIRST_SHIFT_RUNNING_MS = (90 * 60) * 1000  # 07:00, the line has been running for ~1 h


@pytest.fixture(scope="session")
def cfg() -> SimConfig:
    return load_config(CONFIG_DIR)


@pytest.fixture(scope="session")
def reg_map() -> RegisterMap:
    return RegisterMap.load()


@pytest.fixture
def runtime(cfg: SimConfig, reg_map: RegisterMap) -> SimRuntime:
    return SimRuntime(cfg, reg_map, seed=42)


@pytest.fixture
def stubbed(runtime: SimRuntime) -> tuple[SimRuntime, StubController]:
    """Runtime driven by the Phase 1 stub controller."""
    return runtime, attach(runtime)


@pytest.fixture
def quiet(stubbed: tuple[SimRuntime, StubController]) -> SimRuntime:
    """Stubbed runtime without random faults, so a test sees only what it injects."""
    rt, _ = stubbed
    rt.plant.scheduler.enabled = False
    return rt
