"""Loads contracts/modbus/sim-io.yaml and converts between engineering values and raw registers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

SignalType = Literal["di", "ir", "coil", "hr"]
BIT_TYPES: tuple[SignalType, ...] = ("di", "coil")
WORD_TYPES: tuple[SignalType, ...] = ("ir", "hr")
DEFAULT_MAP_PATH = Path(__file__).resolve().parents[4] / "contracts" / "modbus" / "sim-io.yaml"


@dataclass(frozen=True)
class Signal:
    name: str
    unit_id: int
    type: SignalType
    addr: int
    scale: float = 1.0
    words: int = 1
    eng_unit: str = ""
    is_bit: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "is_bit", self.type in BIT_TYPES)

    def encode(self, value: float | bool) -> list[int]:
        """Engineering value → raw words (bit signals return [0|1])."""
        if self.is_bit:
            return [1 if value else 0]
        raw = int(round(float(value) * self.scale))
        if self.words == 2:
            raw %= 1 << 32
            return [raw >> 16, raw & 0xFFFF]
        return [min(max(raw, 0), 0xFFFF)]

    def decode(self, raw: list[int]) -> float | bool:
        if self.is_bit:
            return bool(raw[0])
        value = (raw[0] << 16 | raw[1]) if self.words == 2 else raw[0]
        return value / self.scale


class RegisterMap:
    def __init__(self, signals: list[Signal], equipment: dict[int, str]) -> None:
        self.signals = {s.name: s for s in signals}
        self.equipment = equipment
        if len(self.signals) != len(signals):
            raise ValueError("duplicate signal names in register map")
        self._check_overlaps(signals)

    @classmethod
    def load(cls, path: Path = DEFAULT_MAP_PATH) -> RegisterMap:
        doc = yaml.safe_load(path.read_text())
        signals: list[Signal] = []
        equipment: dict[int, str] = {}
        for unit_id, unit in doc["units"].items():
            equipment[int(unit_id)] = unit["equipment"]
            for s in unit["signals"]:
                signals.append(
                    Signal(
                        name=s["name"],
                        unit_id=int(unit_id),
                        type=s["type"],
                        addr=int(s["addr"]),
                        scale=float(s.get("scale", 1)),
                        words=int(s.get("words", 1)),
                        eng_unit=str(s.get("unit", "")),
                    )
                )
        return cls(signals, equipment)

    def size(self, unit_id: int, type_: SignalType) -> int:
        ends = [s.addr + s.words for s in self.signals.values()
                if s.unit_id == unit_id and s.type == type_]
        return max(ends, default=0)

    @staticmethod
    def _check_overlaps(signals: list[Signal]) -> None:
        used: dict[tuple[int, str, int], str] = {}
        for s in signals:
            for offset in range(s.words):
                key = (s.unit_id, s.type, s.addr + offset)
                if key in used:
                    raise ValueError(f"{s.name} overlaps {used[key]} at {key}")
                used[key] = s.name
