"""PLC-04 / contracts.md §6: every sim-io.yaml signal is mapped at the right OpenPLC address, and
only the generated IO_* / Bridge_* programs touch located addresses. Needs no running stack.

The expected addresses are recomputed here from OpenPLC's packing rule (ADR 0005), independently
of plc/scripts/codegen, so a generator bug cannot hide behind itself."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "plc" / "src"
DECL = re.compile(r"^\s*(\w+)\s+AT\s+(%[IQM][XWD][\d.]+)\s*:", re.MULTILINE)


def expected_addresses() -> dict[str, str]:
    units = yaml.safe_load((ROOT / "contracts/modbus/sim-io.yaml").read_text())["units"]
    offset = {"di": 0, "coil": 0, "ir": 0, "hr": 0}
    expected: dict[str, str] = {}
    for _, unit in sorted(units.items(), key=lambda kv: int(kv[0])):
        size = dict.fromkeys(offset, 0)
        for s in unit["signals"]:
            words = s.get("words", 1)
            size[s["type"]] = max(size[s["type"]], s["addr"] + words)
            for w in range(words):
                index = offset[s["type"]] + s["addr"] + w
                name = s["name"] if words == 1 else f"{s['name']}_{'HI' if w == 0 else 'LO'}"
                expected[name] = {
                    "di": f"%IX{100 + index // 8}.{index % 8}",
                    "coil": f"%QX{100 + index // 8}.{index % 8}",
                    "ir": f"%IW{100 + index}",
                    "hr": f"%QW{100 + index}",
                }[s["type"]]
        for t in offset:
            offset[t] += size[t]
    return expected


def test_io_map_matches_contract() -> None:
    mapped: dict[str, str] = {}
    for f in (SRC / "generated" / "io").glob("IO_*.st"):
        mapped |= dict(DECL.findall(f.read_text()))
    expected = expected_addresses()
    assert set(mapped) == set(expected), "signals missing from or extra in IO_*"
    wrong = {n: (mapped[n], a) for n, a in expected.items() if mapped[n] != a}
    assert not wrong, f"wrong address (mapped, expected): {wrong}"


def test_slave_config_polls_every_unit() -> None:
    cfg = (ROOT / "plc/runtime/mbconfig.cfg").read_text()
    units = yaml.safe_load((ROOT / "contracts/modbus/sim-io.yaml").read_text())["units"]
    assert f'Num_Devices = "{len(units)}"' in cfg
    for uid in units:
        assert f'slave_id = "{uid}"' in cfg


def test_logic_never_touches_addresses() -> None:
    offenders = [
        str(f.relative_to(SRC)) for f in SRC.rglob("*.st")
        if "generated" not in f.parts and DECL.search(f.read_text())
    ]
    assert not offenders, f"located variables outside the generated maps: {offenders}"
