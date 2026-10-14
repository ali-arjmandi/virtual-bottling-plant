"""Fault specs per machine, from config/faults.yaml."""

from __future__ import annotations

from sim.config_models import FaultSpec


class FaultCatalog:
    def __init__(self, faults: dict[str, list[FaultSpec]]) -> None:
        self._faults = faults

    def machines(self) -> list[str]:
        return list(self._faults)

    def for_machine(self, machine: str) -> list[FaultSpec]:
        return self._faults.get(machine, [])

    def get(self, machine: str, fault_type: str) -> FaultSpec:
        for spec in self.for_machine(machine):
            if spec.type == fault_type:
                return spec
        raise KeyError(f"unknown fault {machine}/{fault_type}")
