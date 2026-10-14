"""Bridge_* programs: the only code with %MW/%MD (PLC ↔ edge bridge, plc-io.yaml)."""

from __future__ import annotations

from codegen.contracts import Device, PlcIo, SimSignal
from codegen.sources import counter_source, metric_source
from codegen.st_format import banner, from_int_word, program, to_int_word, word_type

SRC = "contracts/modbus/plc-io.yaml"
GLOBAL_TYPES = {"G_In": "ST_SimInputs", "G_Out": "ST_SimOutputs", "G_Status": "ST_Status",
                "G_Comms": "ST_CommsStatus", "G_Alarms": "ST_AlarmSummary",
                "G_Counters": "ST_Counters", "G_Cmd": "ST_Commands",
                "G_RecipeReq": "ST_RecipeRequest", "G_RecipeResp": "ST_RecipeResponse"}


def _externals(body: list[str]) -> list[str]:
    text = "\n".join(body)
    return [f"{g} : {t};" for g, t in GLOBAL_TYPES.items() if f"{g}." in text]


def _device(device: Device, signals: dict[str, SimSignal]) -> str:
    decls, body = [], []
    for m in sorted(device.metrics, key=lambda m: m.offset):
        var = f"{device.name}_{m.name}" if not m.name.startswith(device.name) else m.name
        src = metric_source(m, device, signals)
        decls.append(f"{var} AT %MW{device.base + m.offset} : INT;")
        body.append(f"{var} := {to_int_word(src.expr, src.st_type, m.scale)};")
    if device.nozzles:
        nz = device.nozzles
        for n in range(1, nz["count"] + 1):
            for i, (fld, scale) in enumerate(zip(nz["fields"], nz["scale"], strict=True)):
                var = f"Q701_N{n:02d}_{fld}"
                mw = device.base + nz["first_offset"] + 3 * (n - 1) + i
                decls.append(f"{var} AT %MW{mw} : INT;")
                body.append(f"{var} := {to_int_word('G_In.' + var, signals[var].st_type, scale)};")
    header = banner(SRC, f"Status block {device.name} (%MW{device.base}…).")
    return program(f"Bridge_{device.name}", header, _externals(body), decls, body)


def _alarms(plc: PlcIo) -> str:
    decls = [f"ALM_{a.name} AT %MW{plc.alarm_base + a.id} : INT;" for a in plc.alarms]
    body = [f"ALM_{a.name} := UINT_TO_INT(G_Alarms.W{a.id});" for a in plc.alarms]
    header = banner(SRC, "Alarm table: bit0 active, bit1 acked, bit2 first-out, bits 8-11 prio.")
    return program("Bridge_Alarms", header, _externals(body), decls, body)


def _counters(plc: PlcIo, signals: dict[str, SimSignal]) -> str:
    decls, body = [], []
    for c in plc.counters:
        src = counter_source(c, signals)
        decls.append(f"{c['name']} AT %MD{c['md']} : DINT;")
        body.append(f"{c['name']} := UDINT_TO_DINT({src.expr});")
    header = banner(SRC, "32-bit counters (%MD, high word first on Modbus).")
    return program("Bridge_Counters", header, _externals(body), decls, body)


def _commands(plc: PlcIo) -> str:
    decls, body = [], []
    for c in plc.commands:
        decls.append(f"{c['name']} AT %MW{c['mw']} : INT;")
        raw = from_int_word(c["name"], word_type(c), float(c.get("scale", 1)))
        body += [f"G_Cmd.{c['name']} := {raw};", f"{c['name']} := 0;"]
    header = banner(SRC, "One-shot commands: valid in G_Cmd for the scan they arrive, then 0.")
    return program("Bridge_Commands", header, _externals(body), decls, body)


def _recipe(plc: PlcIo) -> str:
    decls, body = [], []
    for r in plc.recipe_request:
        decls.append(f"{r['name']} AT %MW{r['mw']} : INT;")
        raw = from_int_word(r["name"], word_type(r), float(r.get("scale", 1)))
        body.append(f"G_RecipeReq.{r['name']} := {raw};")
    for r in plc.recipe_response:
        decls.append(f"{r['name']} AT %MW{r['mw']} : INT;")
        body.append(f"{r['name']} := {to_int_word('G_RecipeResp.' + r['name'], word_type(r))};")
    header = banner(SRC, "Recipe download block and Req/Ack/Nak handshake (contracts.md §2).")
    return program("Bridge_Recipe", header, _externals(body), decls, body)


def bridge_programs(plc: PlcIo, signals: dict[str, SimSignal]) -> dict[str, str]:
    files = {f"Bridge_{d.name}.st": _device(d, signals) for d in plc.devices}
    files["Bridge_Alarms.st"] = _alarms(plc)
    files["Bridge_Counters.st"] = _counters(plc, signals)
    files["Bridge_Commands.st"] = _commands(plc)
    files["Bridge_Recipe.st"] = _recipe(plc)
    return files
