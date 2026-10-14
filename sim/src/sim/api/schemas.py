"""Request bodies of the simulator API (docs/prd/contracts.md §4). JSON uses camelCase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class FaultRequest(Body):
    machine: str = Field(examples=["C501"])
    type: str = Field(examples=["jam"])
    duration_s: float | None = Field(default=None, gt=0)
    params: dict[str, float] = {}


class SensorOverrideRequest(Body):
    mode: Literal["stuck", "disconnect", "noise"]
    value: float | None = None


class ClockRequest(Body):
    speed: Literal[1, 10, 60] | None = None
    paused: bool | None = None


class ResetRequest(Body):
    seed: int = 42
