"""FB_AlarmTable: one FB_Alarm instance per alarm in plc-io.yaml (PLC-20..22), plus the
per-device summary (alarm word, first active id) and the line first-out."""

from __future__ import annotations

from codegen.contracts import PlcIo
from codegen.st_format import banner, var_block


def alarm_table_fb(plc: PlcIo) -> str:
    inputs = ["AckId : INT; (* alarm id, -1 = all, 0 = none *)"]
    inputs += [f"{a.name} : BOOL; (* {a.id}, P{a.priority}: {a.text} *)" for a in plc.alarms]
    locals_ = [f"Alm_{a.name} : FB_Alarm;" for a in plc.alarms]
    locals_ += ["FirstOutFree : BOOL := TRUE;", "Standing : INT;", "StandingLastScan : INT;"]
    body = [
        "(* First-out re-arms once every alarm is cleared and acknowledged. The line's",
        "   FirstOutId follows the alarm holding the flag, so it drops to 0 as soon as that",
        "   alarm is cleared and acked, even while other alarms are still shown. *)",
        "IF StandingLastScan = 0 THEN",
        "  FirstOutFree := TRUE;",
        "END_IF;",
        "Summary.FirstOutId := 0;",
        "Standing := 0;",
        "Summary.ActiveCount := 0;",
    ]
    body += [f"Summary.{d.name}_Word := 0;\nSummary.{d.name}_ActiveId := 0;" for d in plc.devices]
    for a in plc.alarms:
        inst = f"Alm_{a.name}"
        body += [
            f"{inst}(Condition := {a.name}, AckId := AckId, Id := {a.id}, "
            f"Priority := {a.priority}, FirstOutFree := FirstOutFree);",
            f"Summary.W{a.id} := {inst}.StatusWord;",
            f"IF {inst}.Active THEN Summary.{a.device}_Word := Summary.{a.device}_Word + "
            f"{2 ** a.local}; Summary.ActiveCount := Summary.ActiveCount + 1; END_IF;",
            f"IF {inst}.Active AND Summary.{a.device}_ActiveId = 0 THEN "
            f"Summary.{a.device}_ActiveId := {a.id}; END_IF;",
            f"IF {inst}.Shown THEN Standing := Standing + 1; END_IF;",
            f"IF {inst}.FirstOut THEN Summary.FirstOutId := {a.id}; END_IF;",
        ]
    body += ["", "StandingLastScan := Standing;"]
    lines = "".join(f"  {line}\n" for chunk in body for line in chunk.split("\n"))
    return (banner("contracts/modbus/plc-io.yaml", "Line 1 alarm table.")
            + "FUNCTION_BLOCK FB_AlarmTable\n"
            + var_block("VAR_INPUT", inputs)
            + var_block("VAR_OUTPUT", ["Summary : ST_AlarmSummary;"])
            + var_block("VAR", locals_)
            + lines + "END_FUNCTION_BLOCK\n")
