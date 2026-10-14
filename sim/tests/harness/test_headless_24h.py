"""Phase 1 exit criterion: a 24 h run gives OEE 55–70 % with one clear top stop reason."""

from pathlib import Path

import pytest

from harness.headless_run import run


@pytest.mark.slow
@pytest.mark.parametrize("seed", [42, 7])
def test_24h_run_is_plausible(seed: int, tmp_path: Path) -> None:
    summary = run(hours=24, seed=seed, out=tmp_path)
    assert 0.55 <= summary["oee"] <= 0.70
    top, second = summary["pareto"][0], summary["pareto"][1]
    assert top["reason"] == "C501 jam"
    assert top["minutes"] >= 1.5 * second["minutes"]
