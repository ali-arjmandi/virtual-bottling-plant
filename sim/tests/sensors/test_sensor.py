import numpy as np

from sim.config_models import SensorSpec
from sim.rng import NoiseBuffer
from sim.runtime import SimRuntime
from sim.sensors.sensor import Sensor, SensorOverride


def _sensor(sd: float = 0.0, resolution: float = 0.1) -> Sensor:
    return Sensor("TT202_OutTemp", SensorSpec(sd=sd, resolution=resolution),
                  NoiseBuffer(np.random.default_rng(0)))


def test_quantisation() -> None:
    assert abs(_sensor().read(85.234) - 85.2) < 1e-9


def test_noise_is_centred_on_true_value() -> None:
    sensor = _sensor(sd=0.5, resolution=0)
    readings = [sensor.read(85.0) for _ in range(5000)]
    assert abs(np.mean(readings) - 85.0) < 0.05
    assert 0.45 < np.std(readings) < 0.55


def test_stuck_sensor_holds_its_value() -> None:
    sensor = _sensor()
    sensor.read(80.0)
    sensor.set_override(SensorOverride("stuck"))
    assert sensor.read(90.0) == 80.0
    assert sensor.true_value == 90.0


def test_disconnect_takes_the_unit_offline(runtime: SimRuntime) -> None:
    runtime.set_sensor_override("TT202_OutTemp", "disconnect")
    assert runtime.disconnected_units() == {2}
    runtime.set_sensor_override("TT202_OutTemp", None)
    assert runtime.disconnected_units() == set()
