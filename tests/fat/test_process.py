"""Process side: T-301 filler interlock, P-201 divert and PID (l1-plc.md PLC-11, PLC-12)."""

from __future__ import annotations

import time

from conftest import real_s
from plc_client import PlcClient
from sim_api import SimApi
from waiting import holds_for, wait_until


def sim_time_s(plc: PlcClient) -> float:
    return plc.counter("SIM_TimeMs") / 1000.0


def test_buffer_empty_blocks_filler(line: PlcClient, sim: SimApi) -> None:
    sim.override("LT301_Level", "stuck", 15.0)
    wait_until(lambda: not line.get("T301", "FillerPermissive"), real_s(2), "interlock off")
    wait_until(lambda: not sim.state()["machines"]["F401"]["runCmd"], real_s(2), "F-401 run off")
    wait_until(lambda: line.state("F401") == "Suspended" and line.get("F401", "Starved"),
               real_s(5), "F-401 Suspended (starved)")
    sim.override("LT301_Level", "stuck", 22.0)  # above 20 % but below the 25 % restart level
    assert holds_for(lambda: line.state("F401") == "Suspended", real_s(10, margin_s=1))
    sim.override("LT301_Level", "stuck", 30.0)
    wait_until(lambda: line.state("F401") == "Execute", real_s(5), "F-401 back in Execute")
    assert sim.state()["machines"]["F401"]["runCmd"]


def test_low_temp_diverts(line: PlcClient, sim: SimApi) -> None:
    assert not line.get("P201", "XV203_Divert")
    sim.override("TT202_OutTemp", "stuck", 82.0)
    wait_until(lambda: line.get("P201", "XV203_Divert"), 1.5, "divert open")
    assert line.alarm("P201_LowTemp")["active"]
    assert not line.get("P201", "ForwardFlowOk")
    sim.override("TT202_OutTemp", "stuck", 85.0)
    hot_since = sim_time_s(line)
    wait_until(lambda: not line.get("P201", "XV203_Divert"), real_s(45), "divert closed")
    held_s = sim_time_s(line) - hot_since
    assert 29.0 <= held_s <= 40.0, f"divert closed after {held_s:.1f} s stable, expected 30 s"


def test_pid_step_response(line: PlcClient, sim: SimApi) -> None:
    """Acceptance: settles to 85 ± 0.5 °C within 3 min after a 10 °C step, overshoot < 1 °C.
    Run with the line stopped and T-301 full, so the transfer pump does not cycle."""
    line.command("LINE_Cmd", "Stop")
    wait_until(lambda: line.get("T301", "LT301_Level") > 97.0 and line.get("P201", "FT201_Flow") < 100,
               real_s(1800), "T-301 full and the transfer pump off", interval_s=1.0)
    try:
        line.command("P201_TempSP", 75.0)
        wait_until(lambda: holds_for(lambda: abs(line.get("P201", "TT202_OutTemp") - 75.0) < 0.5,
                                     real_s(30, margin_s=0)), real_s(600), "settled at 75 °C")
        line.command("P201_TempSP", 85.0)
        start = sim_time_s(line)
        samples: list[tuple[float, float]] = []
        while sim_time_s(line) - start < 240:
            samples.append((sim_time_s(line) - start, line.get("P201", "TT202_OutTemp")))
            time.sleep(0.1)
        peak = max(t for _, t in samples)
        late = [t for s, t in samples if s >= 180]
        assert peak < 86.0, f"overshoot {peak - 85.0:.2f} °C"
        assert late and all(abs(t - 85.0) <= 0.5 for t in late), \
            f"not settled after 3 min: {min(late):.2f}..{max(late):.2f} °C"
    finally:
        line.command("P201_TempSP", 85.0)
