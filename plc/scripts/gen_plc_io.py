"""Generates the PLC's contract boundary from contracts/modbus/*.yaml.

Writes plc/src/generated/ (types, globals, IO_* and Bridge_* programs, FB_AlarmTable) and
plc/runtime/ (OpenPLC slave-device config, located-address table). Hand-written control logic
never touches a register address. CI runs this with --check.

Usage: python3 plc/scripts/gen_plc_io.py [--check]      (needs PyYAML)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codegen.contracts import ROOT, load_plc_io, load_sim_io  # noqa: E402
from codegen.gen_alarms import alarm_table_fb  # noqa: E402
from codegen.gen_bridge import bridge_programs  # noqa: E402
from codegen.gen_io import io_programs  # noqa: E402
from codegen.gen_types import enums_st, gvl_st, structs_st  # noqa: E402
from codegen.runtime_config import address_table, mbconfig  # noqa: E402
from codegen.sources import resolve_status_fields, sim_signals  # noqa: E402

GENERATED = ROOT / "plc" / "src" / "generated"
RUNTIME = ROOT / "plc" / "runtime"


def outputs() -> dict[Path, str]:
    units = load_sim_io()
    plc = load_plc_io()
    signals = sim_signals(units)
    resolve_status_fields(plc, signals)
    files = {
        RUNTIME / "mbconfig.cfg": mbconfig(units),
        RUNTIME / "io_addresses.csv": address_table(units),
        GENERATED / "types" / "Contract_Enums.st": enums_st(plc),
        GENERATED / "types" / "Contract_Structs.st": structs_st(units, plc),
        GENERATED / "gvl" / "GVL_Contract.st": gvl_st(),
        GENERATED / "alarms" / "FB_AlarmTable.st": alarm_table_fb(plc),
    }
    files |= {GENERATED / "io" / n: s for n, s in io_programs(units).items()}
    files |= {GENERATED / "bridge" / n: s for n, s in bridge_programs(plc, signals).items()}
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if files are out of date")
    args = parser.parse_args()
    files = outputs()
    stale = [p for p, text in files.items() if not p.exists() or p.read_text() != text]
    extra = [p for p in GENERATED.rglob("*.st") if p not in files] if GENERATED.exists() else []
    if args.check:
        for p in stale + extra:
            print(f"out of date: {p.relative_to(ROOT)}")
        if stale or extra:
            print("run: python3 plc/scripts/gen_plc_io.py")
        return 1 if stale or extra else 0
    for p in extra:
        p.unlink()
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p])
    print(f"{len(stale)} written, {len(extra)} removed, {len(files) - len(stale)} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
