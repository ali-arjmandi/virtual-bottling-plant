"""Loads contracts/modbus/sim-io.yaml and plc-io.yaml into typed objects for code generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SIM_IO = ROOT / "contracts" / "modbus" / "sim-io.yaml"
PLC_IO = ROOT / "contracts" / "modbus" / "plc-io.yaml"
ENUM_PREFIX = {"PackMLState": "PML", "PackMLMode": "MODE", "BatchPhase": "PHASE",
               "Command": "CMD", "RecipeNak": "NAK"}


def upper_snake(label: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", label).upper()


# --- sim ↔ PLC ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class SimSignal:
    name: str
    unit_id: int
    type: str  # di | coil | ir | hr
    addr: int
    scale: float = 1.0
    words: int = 1

    @property
    def is_input(self) -> bool:
        return self.type in ("di", "ir")

    @property
    def st_type(self) -> str:
        if self.type in ("di", "coil"):
            return "BOOL"
        if self.words == 2:
            return "UDINT"
        if self.name.endswith(("_Heartbeat", "_Seq")):
            return "UINT"
        return "REAL"

    @property
    def global_expr(self) -> str:
        return f"G_{'In' if self.is_input else 'Out'}.{self.name}"


@dataclass
class SimUnit:
    unit_id: int
    equipment: str
    signals: list[SimSignal]

    def size(self, type_: str) -> int:
        return max((s.addr + s.words for s in self.signals if s.type == type_), default=0)


def load_sim_io(path: Path = SIM_IO) -> list[SimUnit]:
    doc = yaml.safe_load(path.read_text())
    units = []
    for uid, unit in sorted(doc["units"].items(), key=lambda kv: int(kv[0])):
        signals = [SimSignal(s["name"], int(uid), s["type"], int(s["addr"]),
                             float(s.get("scale", 1)), int(s.get("words", 1)))
                   for s in unit["signals"]]
        units.append(SimUnit(int(uid), unit["equipment"], signals))
    return units


# --- PLC ↔ bridge -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Enum:
    name: str
    values: dict[int, str]  # number → literal (PML_STOPPED)

    @property
    def st_type(self) -> str:
        return f"E_{self.name}"


@dataclass(frozen=True)
class Metric:
    name: str
    offset: int
    type: str | None = None   # bool | None
    enum: str | None = None
    scale: float = 1.0
    source: str | None = None

    @property
    def st_type(self) -> str:
        if self.type == "bool":
            return "BOOL"
        if self.enum:
            return f"E_{self.enum}"
        return "REAL" if self.scale != 1.0 else "INT"


@dataclass
class Device:
    name: str
    base: int
    metrics: list[Metric]
    has_header: bool
    nozzles: dict | None = None
    status_fields: list[Metric] = field(default_factory=list)


@dataclass(frozen=True)
class Alarm:
    id: int
    device: str
    local: int
    priority: int
    name: str
    text: str


@dataclass
class PlcIo:
    enums: dict[str, Enum]
    header: list[Metric]
    devices: list[Device]
    alarm_base: int
    alarms: list[Alarm]
    commands: list[dict]
    recipe_request: list[dict]
    recipe_response: list[dict]
    counters: list[dict]


def _metric(d: dict) -> Metric:
    return Metric(d["name"], int(d["offset"]), d.get("type"), d.get("enum"),
                  float(d.get("scale", 1)), d.get("source"))


def _enum(name: str, values: dict) -> Enum:
    prefix = ENUM_PREFIX[name]
    lits = {int(k): f"{prefix}_{upper_snake(v)}" for k, v in values.items()}
    if 0 not in lits:
        lits[0] = f"{prefix}_NONE"
    return Enum(name, dict(sorted(lits.items())))


def load_plc_io(path: Path = PLC_IO) -> PlcIo:
    doc = yaml.safe_load(path.read_text())
    header = [_metric(m) for m in doc["packaging_header"]]
    devices = []
    for name, dev in doc["status"].items():
        has_header = dev.get("header") == "packaging_header"
        metrics = (header if has_header else []) + [_metric(m) for m in dev["metrics"]]
        devices.append(Device(name, int(dev["base"]), metrics, has_header,
                              dev.get("nozzle_subgroups")))
    alarms = [Alarm(int(a["id"]), a["device"], int(a["local"]), int(a["priority"]), a["name"],
                    a["text"]) for a in doc["alarm_table"]["alarms"]]
    return PlcIo(
        enums={k: _enum(k, v) for k, v in doc["enums"].items()},
        header=header, devices=devices, alarm_base=int(doc["alarm_table"]["base"]),
        alarms=alarms, commands=doc["commands"], recipe_request=doc["recipe"]["request"],
        recipe_response=doc["recipe"]["response"], counters=doc["counters"],
    )
