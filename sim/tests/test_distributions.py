import numpy as np
import pytest

from sim.config_models import CountTrigger, Exponential, LogNormal, Uniform, Weibull
from sim.distributions import draw_duration_s, draw_interval

N = 20_000


@pytest.mark.parametrize(
    ("spec", "expected_mean"),
    [
        (Exponential(dist="exponential", mean_s=480), 480),
        (Weibull(dist="weibull", shape=1.5, scale_s=1000), 1000 * 0.9027),
        (CountTrigger(dist="count", mean=4000, sd=50), 4000),
    ],
)
def test_interval_mean_within_5_percent(spec: object, expected_mean: float) -> None:
    rng = np.random.default_rng(1)
    mean = np.mean([draw_interval(spec, rng) for _ in range(N)])  # type: ignore[arg-type]
    assert abs(mean - expected_mean) / expected_mean < 0.05


def test_durations_respect_bounds() -> None:
    rng = np.random.default_rng(2)
    uniform = Uniform(dist="uniform", min_s=10, max_s=60)
    lognormal = LogNormal(dist="lognormal", median_s=900, sigma=0.5, min_s=300, max_s=2700)
    u = [draw_duration_s(uniform, rng) for _ in range(N)]
    ln = [draw_duration_s(lognormal, rng) for _ in range(N)]
    assert min(u) >= 10 and max(u) <= 60
    assert abs(np.mean(u) - 35) / 35 < 0.05
    assert min(ln) >= 300 and max(ln) <= 2700
    assert abs(np.median(ln) - 900) / 900 < 0.05
