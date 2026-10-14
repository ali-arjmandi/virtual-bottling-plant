"""What the fault system needs from anything that can fail."""

from __future__ import annotations

from typing import Protocol

from sim.config_models import FaultSpec


class FaultTarget(Protocol):
    def fault_age(self, count_based: bool) -> float:
        """Running seconds (or cycles) the fault trigger clock advances on."""
        ...

    def set_fault(self, spec: FaultSpec, active: bool, params: dict[str, float]) -> None: ...
