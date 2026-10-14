"""Recipe download handshake, Req/Ack/Nak (PLC-30, PLC-31, contracts.md §2)."""

from __future__ import annotations

from conftest import MACHINES, real_s
from plc_client import PlcClient
from waiting import wait_until

ORANGE = {"RecipeId": 7, "RecipeVersion": 3, "ProductCode": 1, "BrixTarget": 11.5,
          "BrixTol": 0.3, "ConcRatio": 0.162, "FillTargetG": 1005.0, "LineSpeed": 120,
          "CapTorque": 2.2}
NAK = {"InExecute": 1, "BrixOutOfRange": 2}


def download(plc: PlcClient, **overrides: float) -> tuple[int, int]:
    """Bridge side of the handshake. Returns (Ack, Nak) and leaves Req cleared."""
    plc.write_recipe(**(ORANGE | overrides))
    plc.write_recipe(Recipe_Req=1)
    try:
        wait_until(lambda: plc.recipe_word("Recipe_Ack") or plc.recipe_word("Recipe_Nak"), 2,
                   "Ack or Nak")
        return plc.recipe_word("Recipe_Ack"), plc.recipe_word("Recipe_Nak")
    finally:
        plc.write_recipe(Recipe_Req=0)
        wait_until(lambda: not (plc.recipe_word("Recipe_Ack") or plc.recipe_word("Recipe_Nak")),
                   2, "Ack/Nak cleared after Req drops")


def stop_line(plc: PlcClient) -> None:
    plc.command("LINE_Cmd", "Stop")
    wait_until(lambda: all(plc.state(m) == "Stopped" for m in MACHINES), real_s(10), "stopped")


def test_recipe_rejected_in_execute(line: PlcClient) -> None:
    assert line.state("F401") == "Execute"
    assert download(line) == (0, NAK["InExecute"])


def test_recipe_out_of_range(line: PlcClient) -> None:
    stop_line(line)
    assert download(line, BrixTarget=20.0) == (0, NAK["BrixOutOfRange"])
    assert line.get("LINE", "RecipeVersion") != 99


def test_recipe_accepted_when_stopped(line: PlcClient) -> None:
    stop_line(line)
    try:
        assert download(line, RecipeVersion=99, LineSpeed=100, FillTargetG=1010.0) == (1, 0)
        assert line.get("LINE", "RecipeId") == 7
        assert line.get("LINE", "RecipeVersion") == 99
        assert line.get("F401", "SpeedSP") == 100
        assert line.get("F401", "FillTargetG") == 1010.0
        assert line.get("Q701", "RejectLimitG") == 1000.0
    finally:
        download(line)  # back to the reference recipe (same product: no CIP)
