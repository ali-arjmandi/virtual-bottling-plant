"""Typed simulator configuration, loaded from sim/config/*.yaml. Fails fast on bad config."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- distributions -------------------------------------------------------------------------

class Exponential(Strict):
    dist: Literal["exponential"]
    mean_s: float = Field(gt=0)


class Weibull(Strict):
    dist: Literal["weibull"]
    shape: float = Field(gt=0)
    scale_s: float = Field(gt=0)


class LogNormal(Strict):
    dist: Literal["lognormal"]
    median_s: float = Field(gt=0)
    sigma: float = Field(ge=0)
    min_s: float = 0
    max_s: float = float("inf")


class Uniform(Strict):
    dist: Literal["uniform"]
    min_s: float = Field(ge=0)
    max_s: float = Field(ge=0)


class CountTrigger(Strict):
    dist: Literal["count"]
    mean: float = Field(gt=0)
    sd: float = Field(default=0, ge=0)


Duration = Annotated[Uniform | LogNormal | Exponential, Field(discriminator="dist")]
Trigger = Annotated[Exponential | Weibull | CountTrigger, Field(discriminator="dist")]


# --- faults --------------------------------------------------------------------------------

class FaultSpec(Strict):
    type: str
    kind: Literal["micro", "breakdown", "material", "process"]
    signal: str | None = None
    trigger: Trigger
    duration: Duration
    effect: dict[str, float] = {}

    @property
    def stops_machine(self) -> bool:
        return self.kind != "process"


# --- line ----------------------------------------------------------------------------------

class MixTankConfig(Strict):
    capacity_l: float
    water_flow_lpm: float
    conc_flow_lpm: float
    sugar_flow_lpm: float
    drain_flow_lpm: float
    agitator_rpm: float
    mix_tau_s: float
    stratification_bx: float
    product_temp_c: float


class PasteurizerConfig(Strict):
    transfer_flow_lpm: float
    recirc_flow_lpm: float
    tau_s: float
    dead_time_s: float
    gain_c_per_pct: float
    ambient_c: float
    steam_pressure_bar: float


class BufferTankConfig(Strict):
    capacity_l: float
    suction_low_pct: float
    drain_flow_lpm: float


class CipConfig(Strict):
    duration_s: float


class SpeedEfficiency(Strict):
    mean: float
    sd: float
    update_s: float


class DriftConfig(Strict):
    nozzle: int
    rate_g_per_h: float
    start_after_h: float


class RestartUnderfill(Strict):
    bottles: int
    mean_g: float
    sd_g: float


class FillerConfig(Strict):
    nozzles: int
    max_speed_bpm: float
    fill_sd_g: float
    nozzle_offset_sd_g: float
    speed_efficiency: SpeedEfficiency
    drift: DriftConfig
    restart_underfill: RestartUnderfill


class CapperConfig(Strict):
    max_speed_bpm: float
    torque_mean_nm: float
    torque_sd_nm: float
    hopper_caps: int
    hopper_refill_at_pct: float
    refill_delay: Duration


class LabelerConfig(Strict):
    max_speed_bpm: float


class CheckweigherConfig(Strict):
    max_speed_bpm: float
    subgroup_size: int


class CasePackerConfig(Strict):
    max_speed_cpm: float
    bottles_per_case: int


class LineConfig(Strict):
    start_time: str
    tick_ms: int
    mix_tank: MixTankConfig
    pasteurizer: PasteurizerConfig
    buffer_tank: BufferTankConfig
    cip: CipConfig
    filler: FillerConfig
    capper: CapperConfig
    labeler: LabelerConfig
    checkweigher: CheckweigherConfig
    case_packer: CasePackerConfig
    conveyors: dict[str, int]
    status_debounce_s: float


# --- operations, sensors, products ---------------------------------------------------------

class BreakConfig(Strict):
    start: str
    minutes: int


class ShiftConfig(Strict):
    name: str
    start: str
    end: str
    response_factor: float
    breaks: list[BreakConfig] = []


class OperatorConfig(Strict):
    reset_delay: Duration
    start_delay: Duration
    button_pulse_s: float
    handover_stop_min: float = 0


class ShiftsConfig(Strict):
    shifts: list[ShiftConfig]
    working_days: list[int]
    operator: OperatorConfig


class SensorSpec(Strict):
    sd: float = 0
    resolution: float = 0


class ProductSpec(Strict):
    select_code: int
    concentrate_brix: float
    lot_brix_sd: float
    offspec_lot_probability: float
    offspec_brix_delta: float
    lot_volume_l: float
    first_lot_no: int


class ProductsConfig(Strict):
    products: dict[str, ProductSpec]
    sugar_syrup_brix: float


class SimConfig(Strict):
    line: LineConfig
    faults: dict[str, list[FaultSpec]]
    shifts: ShiftsConfig
    sensors: dict[str, SensorSpec]
    products: ProductsConfig


def _read(path: Path) -> object:
    with path.open() as f:
        return yaml.safe_load(f)


def load_config(config_dir: Path) -> SimConfig:
    return SimConfig.model_validate(
        {
            "line": _read(config_dir / "line.yaml"),
            "faults": _read(config_dir / "faults.yaml"),
            "shifts": _read(config_dir / "shifts.yaml"),
            "sensors": _read(config_dir / "sensors.yaml"),
            "products": _read(config_dir / "products.yaml"),
        }
    )
