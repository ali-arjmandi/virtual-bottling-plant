"""All analog sensors of the line, and their overrides from the Instructor Station / tests."""

from __future__ import annotations

from sim.config_models import SensorSpec
from sim.event_log import EventLog
from sim.io.register_map import RegisterMap
from sim.rng import NoiseBuffer, RngFactory
from sim.sensors.sensor import Sensor, SensorOverride


class SensorBank:
    def __init__(
        self, specs: dict[str, SensorSpec], reg_map: RegisterMap, rngs: RngFactory,
        log: EventLog,
    ) -> None:
        self._map = reg_map
        self._log = log
        self.sensors = {
            name: Sensor(name, spec, NoiseBuffer(rngs.stream(f"sensor/{name}")))
            for name, spec in specs.items()
        }
        unknown = set(self.sensors) - set(reg_map.signals)
        if unknown:
            raise ValueError(f"sensors not in register map: {sorted(unknown)}")

    def read(self, name: str, true_value: float) -> float:
        sensor = self.sensors.get(name)
        return sensor.read(true_value) if sensor else true_value

    def set_override(self, name: str, override: SensorOverride | None, t_ms: int) -> None:
        if name not in self.sensors:
            raise KeyError(f"unknown sensor {name}")
        self.sensors[name].set_override(override)
        self._log.emit(t_ms, "sensor_override", self._map.equipment[self.unit_of(name)],
                       tag=name, mode=override.mode if override else "clear")

    def unit_of(self, name: str) -> int:
        return self._map.signals[name].unit_id

    def disconnected_units(self) -> set[int]:
        return {
            self.unit_of(s.name)
            for s in self.sensors.values()
            if s.override and s.override.mode == "disconnect"
        }
