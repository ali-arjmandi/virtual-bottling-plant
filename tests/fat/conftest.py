"""FAT fixtures: the Dockerised sim + PLC (docker compose up), reached through the dev ports.

The sim runs at FAT_SIM_SPEED (default ×10, the validated live speed, risk R1) without random
faults, so every upset in a test is one the test made.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from plc_client import PlcClient  # noqa: E402
from sim_api import SimApi  # noqa: E402
from waiting import wait_until  # noqa: E402

SPEED = int(os.environ.get("FAT_SIM_SPEED", "10"))
MACHINES = ("F401", "C501", "L601", "Q701", "K801")
DEVICES = ("T101", "P201", "T301", *MACHINES, "LINE")


def real_s(sim_seconds: float, margin_s: float = 3.0) -> float:
    """Real-time budget for something that takes sim_seconds, plus Modbus/scan latency."""
    return sim_seconds / SPEED + margin_s


@pytest.fixture(scope="session")
def sim() -> SimApi:
    api = SimApi(os.environ.get("FAT_SIM_URL", "http://127.0.0.1:8000"))
    wait_until(api.healthy, 60, "the sim API")
    return api


@pytest.fixture(scope="session")
def plc() -> Iterator[PlcClient]:
    client = PlcClient(os.environ.get("FAT_PLC_HOST", "127.0.0.1"),
                       int(os.environ.get("FAT_PLC_PORT", "5502")))

    def ready() -> bool:
        try:
            client.connect()
            client.read_mw(0)
            return True
        except Exception:  # noqa: BLE001 - the port proxy accepts before OpenPLC is up
            client.close()
            return False

    wait_until(ready, 180, "the PLC Modbus server", interval_s=1.0)
    yield client
    client.close()


@pytest.fixture(scope="session")
def plant(sim: SimApi, plc: PlcClient) -> SimApi:
    """Fresh sim (seed 42) with product in T-301 and P-201 in forward flow, line stopped."""
    sim.reset(42, random_faults=False)
    sim.clock(speed=SPEED, paused=False)
    plc.command("LINE_Cmd", "Stop")
    wait_until(lambda: all(plc.get(d, "CommsOk") for d in DEVICES), 10, "comms to every unit")
    wait_until(lambda: plc.get("T301", "FillerPermissive") and plc.get("P201", "ForwardFlowOk"),
               real_s(3600), "a first batch in T-301 with P-201 in forward flow", interval_s=1.0)
    return sim


def start_line(plc: PlcClient) -> None:
    plc.command("LINE_Cmd", "Reset")
    time.sleep(0.3)
    plc.command("LINE_Cmd", "Start")
    wait_until(lambda: all(plc.state(m) == "Execute" for m in MACHINES), real_s(120),
               "every packaging machine in Execute")


@pytest.fixture
def line(plant: SimApi, plc: PlcClient) -> Iterator[PlcClient]:
    """The line producing, every alarm acknowledged, no faults or sensor overrides."""
    plant.clear_all()
    plant.clock(speed=SPEED, paused=False)
    wait_until(lambda: all(plc.get(d, "CommsOk") for d in DEVICES), 10, "comms to every unit")
    wait_until(lambda: plc.get("T301", "FillerPermissive"), real_s(1800), "T-301 above 25 %",
               interval_s=1.0)
    start_line(plc)
    plc.ack_all_alarms()
    wait_until(lambda: plc.get("LINE", "FirstOutAlarmId") == 0, 5, "a clear alarm table")
    yield plc
    plant.clear_all()
