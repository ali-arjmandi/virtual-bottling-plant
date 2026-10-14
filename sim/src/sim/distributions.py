"""Draws from the distributions declared in config (fault triggers, durations, delays)."""

from __future__ import annotations

import math

import numpy as np

from sim.config_models import (
    CountTrigger,
    Duration,
    Exponential,
    LogNormal,
    Trigger,
    Uniform,
    Weibull,
)


def draw_duration_s(spec: Duration, rng: np.random.Generator) -> float:
    """Seconds, for repair times, operator delays and similar."""
    if isinstance(spec, Uniform):
        return float(rng.uniform(spec.min_s, spec.max_s))
    if isinstance(spec, LogNormal):
        value = float(rng.lognormal(math.log(spec.median_s), spec.sigma))
        return min(max(value, spec.min_s), spec.max_s)
    if isinstance(spec, Exponential):
        return float(rng.exponential(spec.mean_s))
    raise TypeError(f"unsupported duration {spec!r}")


def draw_interval(spec: Trigger, rng: np.random.Generator) -> float:
    """Running seconds (time triggers) or bottles (count triggers) until the next fault."""
    if isinstance(spec, Exponential):
        return float(rng.exponential(spec.mean_s))
    if isinstance(spec, Weibull):
        return float(spec.scale_s * rng.weibull(spec.shape))
    if isinstance(spec, CountTrigger):
        return max(1.0, float(rng.normal(spec.mean, spec.sd)) if spec.sd else spec.mean)
    raise TypeError(f"unsupported trigger {spec!r}")


def is_count_based(spec: Trigger) -> bool:
    return isinstance(spec, CountTrigger)
