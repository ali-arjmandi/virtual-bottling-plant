"""Stops travel through the accumulation conveyors (SIM-11).

Downstream machines run faster than the filler (V-curve), so in normal running the conveyors
are nearly empty: an upstream stop starves the line at once, a downstream stop is absorbed
until the conveyors fill up, bottle by bottle, towards the filler.
"""

from sim.runtime import SimRuntime
from tests.conftest import FIRST_SHIFT_RUNNING_MS


def _status(rt: SimRuntime, machine: str) -> str:
    return rt.plant.machines[machine].status.status.value


def test_capper_jam_blocks_filler_and_starves_downstream(quiet: SimRuntime) -> None:
    rt = quiet
    rt.run_until(FIRST_SHIFT_RUNNING_MS)
    assert _status(rt, "F401") == "producing"

    rt.inject_fault("C501", "jam", duration_s=300)
    rt.run_for(1_000)
    assert _status(rt, "C501") == "faulted"
    assert rt.image.get_bool("C501_Jam")

    rt.run_for(15_000)  # the 12-bottle monoblock transfer fills within seconds
    assert _status(rt, "F401") == "blocked"
    assert rt.image.get_bool("CV1_Full")
    for machine in ("L601", "Q701", "K801"):
        assert _status(rt, machine) == "starved"


def test_case_packer_jam_is_absorbed_until_conveyors_fill(quiet: SimRuntime) -> None:
    rt = quiet
    rt.run_until(FIRST_SHIFT_RUNNING_MS)
    rt.inject_fault("K801", "jam", duration_s=600)

    rt.run_for(60_000)
    assert _status(rt, "F401") == "producing"
    assert _status(rt, "Q701") == "producing"
    assert rt.plant.conveyors["CV4"].fill > 50

    rt.run_for(300_000)  # CV4, CV3, CV2 and CV1 fill one after another
    for machine in ("Q701", "L601", "C501", "F401"):
        assert _status(rt, machine) == "blocked"


def test_line_recovers_after_reset(quiet: SimRuntime) -> None:
    rt = quiet
    rt.run_until(FIRST_SHIFT_RUNNING_MS)
    rt.inject_fault("C501", "jam", duration_s=20)
    rt.run_for(60_000)
    cycles = rt.plant.capper.cycles
    rt.run_for(5 * 60_000)  # fault cleared, operator pressed reset, line restarted
    assert _status(rt, "C501") == "producing"
    assert _status(rt, "F401") == "producing"
    assert rt.plant.capper.cycles > cycles
