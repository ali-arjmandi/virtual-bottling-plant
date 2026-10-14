from sim.physics.tank import Tank


def test_mass_balance_closes() -> None:
    tank = Tank(capacity_l=1000)
    tank.add(600, brix=10)
    removed, _ = tank.remove(250)
    assert removed == 250
    assert tank.volume_l == 350


def test_overflow_is_lost_and_remove_is_clamped() -> None:
    tank = Tank(capacity_l=100)
    assert tank.add(150) == 100
    removed, _ = tank.remove(500)
    assert removed == 100
    assert tank.is_empty


def test_brix_follows_mixing_ratio() -> None:
    tank = Tank(capacity_l=10_000)
    tank.add(800, brix=65)
    tank.add(4200, brix=0)
    assert abs(tank.brix - 65 * 800 / 5000) < 1e-9
    _, brix_out = tank.remove(1000)
    assert abs(brix_out - tank.brix) < 1e-9
