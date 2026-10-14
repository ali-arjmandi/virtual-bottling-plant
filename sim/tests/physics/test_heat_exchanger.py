import math

from sim.physics.heat_exchanger import HeatExchanger

TICK_S = 0.1


def _make() -> HeatExchanger:
    return HeatExchanger(tau_s=40, dead_time_s=5, tick_s=TICK_S, gain_c_per_pct=1.0,
                         nominal_flow_lpm=300, initial_c=20.0)


def test_step_response_has_dead_time_and_time_constant() -> None:
    hx = _make()
    ticks_dead = round(5 / TICK_S)
    for _ in range(ticks_dead):
        hx.step(30.0)
    assert abs(hx.outlet_c - 20.0) < 1e-9  # nothing happens during the dead time

    for _ in range(round(40 / TICK_S)):
        hx.step(30.0)
    expected = 20.0 + 10.0 * (1 - math.exp(-1))  # 63 % after one tau
    assert abs(hx.outlet_c - expected) < 0.1


def test_steady_state_rises_with_steam_and_falls_with_flow() -> None:
    hx = _make()
    base = hx.steady_state_c(12, valve_pct=50, pressure_ratio=1, flow_lpm=300)
    assert hx.steady_state_c(12, 60, 1, 300) > base
    assert hx.steady_state_c(12, 50, 1, 400) < base
    assert hx.steady_state_c(12, 50, 0.5, 300) < base
