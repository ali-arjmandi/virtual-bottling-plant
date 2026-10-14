"""Generated types and globals at the contract boundary: enums (+ INT conversions), the sim I/O
image structs, status/command/recipe structs and the global variable list."""

from __future__ import annotations

from codegen.contracts import PlcIo, SimUnit
from codegen.sources import status_type_name
from codegen.st_format import banner, var_block, word_type

BOTH = "contracts/modbus/sim-io.yaml + plc-io.yaml"


def enums_st(plc: PlcIo) -> str:
    out = banner("contracts/modbus/plc-io.yaml", "Enums with fixed contract numbers. matiec "
                 "enums cannot carry values, so XToInt / IntToX convert at the boundary.")
    out += "TYPE\n" + "".join(
        f"  {e.st_type} : ({', '.join(e.values.values())});\n" for e in plc.enums.values())
    out += "END_TYPE\n"
    for e in plc.enums.values():
        first = next(iter(e.values.values()))
        cases = "".join(f"    {lit}: {e.name}ToInt := {n};\n" for n, lit in e.values.items())
        out += (f"\nFUNCTION {e.name}ToInt : INT\n" + var_block("VAR_INPUT", [f"In : {e.st_type};"])
                + f"  CASE In OF\n{cases}  END_CASE;\nEND_FUNCTION\n")
        cases = "".join(f"    {n}: IntTo{e.name} := {lit};\n" for n, lit in e.values.items())
        out += (f"\nFUNCTION IntTo{e.name} : {e.st_type}\n" + var_block("VAR_INPUT", ["In : INT;"])
                + f"  IntTo{e.name} := {first};\n  CASE In OF\n{cases}  END_CASE;\nEND_FUNCTION\n")
    return out


def _struct(name: str, fields: list[str]) -> str:
    return f"  {name} : STRUCT\n" + "".join(f"    {f}\n" for f in fields) + "  END_STRUCT;\n"


def structs_st(units: list[SimUnit], plc: PlcIo) -> str:
    signals = [s for u in units for s in u.signals]
    out = banner(BOTH, "Process image (sim I/O in engineering units) and bridge structs.")
    out += "TYPE\n"
    out += _struct("ST_SimInputs", [f"{s.name} : {s.st_type};" for s in signals if s.is_input])
    out += _struct("ST_SimOutputs", [f"{s.name} : {s.st_type};" for s in signals if not s.is_input])
    done: set[str] = set()
    for d in plc.devices:
        t = status_type_name(d, plc)
        if t not in done:
            done.add(t)
            out += _struct(t, [f"{m.name} : {m.st_type};" for m in d.status_fields])
    out += _struct("ST_Status", [f"{d.name} : {status_type_name(d, plc)};" for d in plc.devices])
    out += _struct("ST_CommsStatus", [f"{d.name} : BOOL;" for d in plc.devices])
    summary = [f"{d.name}_Word : INT;" for d in plc.devices]
    summary += [f"{d.name}_ActiveId : INT;" for d in plc.devices]
    summary += ["ActiveCount : INT;", "FirstOutId : INT;"]
    summary += [f"W{a.id} : UINT;" for a in plc.alarms]
    out += _struct("ST_AlarmSummary", summary)
    names = {s.name for s in signals}
    out += _struct("ST_Counters", [f"{c['name']} : UDINT;" for c in plc.counters
                                   if c["name"] not in names])
    out += _struct("ST_Commands", [f"{c['name']} : {word_type(c)};" for c in plc.commands])
    out += _struct("ST_RecipeRequest", [f"{r['name']} : {word_type(r)};"
                                        for r in plc.recipe_request])
    out += _struct("ST_RecipeResponse", [f"{r['name']} : {word_type(r)};"
                                         for r in plc.recipe_response])
    return out + "END_TYPE\n"


def gvl_st() -> str:
    out = banner(BOTH, "Global process image. Only the generated IO_* / Bridge_* programs and "
                 "PRG_Main use these.")
    decls = ["G_In : ST_SimInputs;", "G_Out : ST_SimOutputs;", "G_Status : ST_Status;",
             "G_Comms : ST_CommsStatus;", "G_Alarms : ST_AlarmSummary;",
             "G_Counters : ST_Counters;", "G_Cmd : ST_Commands;",
             "G_RecipeReq : ST_RecipeRequest;", "G_RecipeResp : ST_RecipeResponse;"]
    return out + var_block("VAR_GLOBAL", decls)
