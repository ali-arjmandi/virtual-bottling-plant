"""Packaging line: PackML states, blocked/starved cascade, alarms, comms loss (l1-plc.md FAT)."""

from __future__ import annotations

import time

from conftest import MACHINES, real_s
from plc_client import PlcClient
from sim_api import SimApi
from waiting import wait_until

C501_JAM = 10
C501_COMMS_LOST = 13


def test_line_stop_and_start_command(line: PlcClient) -> None:
    line.command("LINE_Cmd", "Stop")
    wait_until(lambda: all(line.state(m) == "Stopped" for m in MACHINES), real_s(10),
               "every machine Stopped")
    assert not line.get("F401", "Running")
    line.command("LINE_Cmd", "Start")  # from Stopped: the sequencer resets, then starts
    wait_until(lambda: all(line.state(m) == "Execute" for m in MACHINES), real_s(60),
               "every machine back in Execute")


def test_capper_jam_cascade(line: PlcClient, sim: SimApi) -> None:
    sim.fault("C501", "jam", duration_s=60)
    wait_until(lambda: line.state("C501") == "Held", real_s(3), "C-501 Held")
    assert line.get("C501", "StopReason") == C501_JAM  # automatic reason = alarm id
    assert line.alarm("C501_Jam")["active"]
    # F-401 keeps filling until the 12-bottle monoblock transfer CV1 is full, then is blocked
    wait_until(lambda: line.state("F401") == "Suspended", real_s(20), "F-401 Suspended")
    assert line.get("F401", "Blocked")
    # downstream runs dry: L-601 onwards starved
    wait_until(lambda: line.state("L601") == "Suspended" and line.get("L601", "Starved"),
               real_s(20), "L-601 Suspended (starved)")
    # jam clears after 60 s; the sim operator presses reset; everything recovers by itself
    wait_until(lambda: all(line.state(m) == "Execute" for m in MACHINES), real_s(60 + 240),
               "the whole line back in Execute")
    assert line.get("C501", "StopReason") == 0


def test_first_out_alarm(line: PlcClient, sim: SimApi) -> None:
    sim.fault("C501", "jam", duration_s=60)
    wait_until(lambda: line.alarm("C501_Jam")["active"], real_s(3), "C501_Jam active")
    time.sleep(real_s(2, margin_s=0.5))
    sim.fault("L601", "label_error", duration_s=60)
    wait_until(lambda: line.alarm("L601_LabelError")["active"], real_s(3), "L601_LabelError")
    assert line.alarm("C501_Jam")["first_out"]
    assert not line.alarm("L601_LabelError")["first_out"]
    assert line.get("LINE", "FirstOutAlarmId") == C501_JAM
    assert line.alarm("C501_Jam")["priority"] == 2
    line.command("AlarmAck", C501_JAM)
    wait_until(lambda: line.alarm("C501_Jam")["acked"], 3, "C501_Jam acknowledged")
    assert not line.alarm("L601_LabelError")["acked"]


def test_comms_loss(line: PlcClient, sim: SimApi) -> None:
    sim.override("C501_Torque", "disconnect")  # unit 5 stops answering
    wait_until(lambda: not line.get("C501", "CommsOk"), 4, "C-501 comms lost")
    assert line.alarm("C501_CommsLost")["active"]
    wait_until(lambda: line.state("C501") == "Held", real_s(3), "C-501 Held")
    assert line.get("C501", "StopReason") == C501_COMMS_LOST
    assert line.get("F401", "CommsOk")  # other stations are unaffected
    sim.clear_override("C501_Torque")
    wait_until(lambda: line.get("C501", "CommsOk"), 4, "C-501 comms back")
    line.command("LINE_Cmd", "Reset")
    wait_until(lambda: line.state("C501") == "Execute", real_s(20), "C-501 back in Execute")
