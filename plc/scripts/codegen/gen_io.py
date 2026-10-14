"""IO_<EQ> programs: one per sim unit (remote I/O station). The only code with %IX/%QX/%IW/%QW
(PLC-04): raw registers ↔ engineering values in G_In / G_Out."""

from __future__ import annotations

from codegen.contracts import SimUnit
from codegen.runtime_config import Located, located_addresses
from codegen.st_format import banner, num, program


def _line(row: Located) -> str | None:
    s = row.signal
    if s.type == "di":
        return f"G_In.{s.name} := {row.var};"
    if s.type == "coil":
        return f"{row.var} := G_Out.{s.name};"
    if s.words == 2:
        if row.word == 1:
            return None
        return f"G_In.{s.name} := UINT_TO_UDINT({s.name}_HI) * 65536 + UINT_TO_UDINT({s.name}_LO);"
    if s.type == "ir":
        if s.st_type == "UINT":
            return f"G_In.{s.name} := {row.var};"
        div = "" if s.scale == 1.0 else f" / {num(s.scale)}"
        return f"G_In.{s.name} := UINT_TO_REAL({row.var}){div};"
    mul = "" if s.scale == 1.0 else f" * {num(s.scale)}"
    return f"{row.var} := REAL_TO_UINT(LIMIT(0.0, G_Out.{s.name}{mul}, 65535.0));"


def io_programs(units: list[SimUnit]) -> dict[str, str]:
    """File name → ST source."""
    located = located_addresses(units)
    files = {}
    for unit in units:
        rows = located[unit.unit_id]
        externals = []
        if any(r.signal.is_input for r in rows):
            externals.append("G_In : ST_SimInputs;")
        if any(not r.signal.is_input for r in rows):
            externals.append("G_Out : ST_SimOutputs;")
        decls = [f"{r.var} AT {r.address} : {'BOOL' if r.signal.st_type == 'BOOL' else 'UINT'};"
                 for r in rows]
        body = [line for r in rows if (line := _line(r))]
        header = banner("contracts/modbus/sim-io.yaml",
                        f"Remote I/O station {unit.equipment} (Modbus unit {unit.unit_id}).")
        name = f"IO_{unit.equipment}"
        files[f"{name}.st"] = program(name, header, externals, decls, body)
    return files
