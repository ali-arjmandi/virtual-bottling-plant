import pytest

from sim.runtime import SimRuntime


def test_fault_sets_signal_until_it_expires(runtime: SimRuntime) -> None:
    fault = runtime.inject_fault("K801", "jam", duration_s=30)
    runtime.run_for(1_000)
    assert runtime.image.get_bool("K801_Jam")
    runtime.run_for(30_000)
    assert not runtime.image.get_bool("K801_Jam")
    assert not runtime.plant.injector.is_active("K801", "jam")
    assert fault["durationS"] == 30


def test_clear_fault_early(runtime: SimRuntime) -> None:
    fault = runtime.inject_fault("C501", "jam", duration_s=600)
    runtime.run_for(1_000)
    assert runtime.clear_fault(fault["id"])
    runtime.run_for(200)
    assert not runtime.image.get_bool("C501_Jam")
    assert not runtime.clear_fault(fault["id"])


def test_steam_drop_lowers_pressure(runtime: SimRuntime) -> None:
    runtime.inject_fault("P201", "steam_drop", duration_s=60)
    runtime.run_for(1_000)
    assert runtime.image.get_float("PT201_SteamPressure") < 2.0


def test_unknown_fault_is_rejected(runtime: SimRuntime) -> None:
    with pytest.raises(KeyError):
        runtime.inject_fault("C501", "meteor")


def test_label_roll_runs_out_after_its_count(runtime: SimRuntime) -> None:
    remaining = runtime.plant.scheduler.remaining("L601", "roll_empty")
    assert remaining == 4000
