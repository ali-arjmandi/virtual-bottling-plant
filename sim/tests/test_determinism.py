"""Same seed, same run (SIM-60)."""

import io

from harness.stub_controller import attach
from sim.config_models import SimConfig
from sim.io.register_map import RegisterMap
from sim.runtime import SimRuntime

RUN_MS = 2 * 3600 * 1000


def _run(cfg: SimConfig, reg_map: RegisterMap, seed: int) -> str:
    sink = io.StringIO()
    rt = SimRuntime(cfg, reg_map, seed, sink)
    attach(rt)
    rt.run_until(RUN_MS)
    return sink.getvalue()


def test_same_seed_gives_identical_event_log(cfg: SimConfig, reg_map: RegisterMap) -> None:
    first, second = _run(cfg, reg_map, 7), _run(cfg, reg_map, 7)
    assert first.count("\n") > 50
    assert first == second


def test_different_seed_gives_different_run(cfg: SimConfig, reg_map: RegisterMap) -> None:
    assert _run(cfg, reg_map, 7) != _run(cfg, reg_map, 8)
