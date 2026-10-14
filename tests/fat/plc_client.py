"""The PLC as the edge bridge sees it: Modbus TCP to %MW/%MD, decoded with plc-io.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pymodbus.client import ModbusTcpClient

PLC_IO = Path(__file__).resolve().parents[2] / "contracts" / "modbus" / "plc-io.yaml"


@dataclass(frozen=True)
class Word:
    mw: int
    scale: float = 1.0
    enum: dict[int, str] | None = None
    is_bool: bool = False


def _signed(raw: int) -> int:
    return raw - 0x10000 if raw >= 0x8000 else raw


class PlcClient:
    def __init__(self, host: str, port: int) -> None:
        self.doc: dict[str, Any] = yaml.safe_load(PLC_IO.read_text())
        self.mw_base = self.doc["addressing"]["mw_holding_base"]
        self.md_base = self.doc["addressing"]["md_holding_base"]
        self.client = ModbusTcpClient(host, port=port, timeout=2, retries=1)
        self.status = self._status_words()
        self.alarm_ids = {a["name"]: a["id"] for a in self.doc["alarm_table"]["alarms"]}
        self.commands = {c["name"]: c for c in self.doc["commands"]}
        self.recipe = {r["name"]: r for r in self.doc["recipe"]["request"]
                       + self.doc["recipe"]["response"]}
        self.counters = {c["name"]: c["md"] for c in self.doc["counters"]}

    def _status_words(self) -> dict[tuple[str, str], Word]:
        words = {}
        enums = {k: {int(n): v for n, v in e.items()} for k, e in self.doc["enums"].items()}
        for device, block in self.doc["status"].items():
            metrics = (self.doc["packaging_header"] if block.get("header") else []) + block["metrics"]
            for m in metrics:
                words[(device, m["name"])] = Word(
                    block["base"] + m["offset"], float(m.get("scale", 1)),
                    enums.get(m.get("enum", "")), m.get("type") == "bool")
        return words

    def connect(self) -> bool:
        return bool(self.client.connect())

    def close(self) -> None:
        self.client.close()

    # --- raw ------------------------------------------------------------------------------

    def read_mw(self, mw: int, count: int = 1) -> list[int]:
        result = self.client.read_holding_registers(self.mw_base + mw, count=count)
        if result.isError():
            raise ConnectionError(f"read %MW{mw}: {result}")
        return [_signed(r) for r in result.registers]

    def write_mw(self, mw: int, value: int) -> None:
        result = self.client.write_register(self.mw_base + mw, value & 0xFFFF)
        if result.isError():
            raise ConnectionError(f"write %MW{mw}: {result}")

    # --- named ----------------------------------------------------------------------------

    def get(self, device: str, metric: str) -> Any:
        """Engineering value: str for enums, bool, or float."""
        w = self.status[(device, metric)]
        raw = self.read_mw(w.mw)[0]
        if w.enum is not None:
            return w.enum.get(raw, f"?{raw}")
        if w.is_bool:
            return raw != 0
        return raw / w.scale

    def state(self, device: str) -> str:
        return str(self.get(device, "State"))

    def counter(self, name: str) -> int:
        md = self.counters[name]
        hi, lo = self.client.read_holding_registers(self.md_base + 2 * md, count=2).registers
        return hi << 16 | lo

    def alarm(self, name: str) -> dict[str, Any]:
        raw = self.read_mw(self.doc["alarm_table"]["base"] + self.alarm_ids[name])[0] & 0xFFFF
        return {"active": bool(raw & 1), "acked": bool(raw & 2), "first_out": bool(raw & 4),
                "priority": (raw >> 8) & 0xF}

    def command(self, name: str, value: float | str) -> None:
        c = self.commands[name]
        if isinstance(value, str):
            value = {v: k for k, v in self.doc["enums"][c["enum"]].items()}[value]
        self.write_mw(c["mw"], round(float(value) * float(c.get("scale", 1))))

    def ack_all_alarms(self) -> None:
        self.command("AlarmAck", -1)

    def write_recipe(self, **values: float) -> None:
        """Writes recipe values (engineering units), not the request bit."""
        for name, value in values.items():
            r = self.recipe[name]
            self.write_mw(r["mw"], round(float(value) * float(r.get("scale", 1))))

    def recipe_word(self, name: str) -> int:
        return self.read_mw(self.recipe[name]["mw"])[0]
