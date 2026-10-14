"""Tank mass balance with dissolved solids, so Brix follows the mix (SIM-01, SIM-03)."""

from __future__ import annotations


class Tank:
    def __init__(self, capacity_l: float, volume_l: float = 0.0) -> None:
        self.capacity_l = capacity_l
        self.volume_l = volume_l
        self.solids = 0.0  # Brix × litres

    @property
    def level_pct(self) -> float:
        return 100.0 * self.volume_l / self.capacity_l

    @property
    def brix(self) -> float:
        return self.solids / self.volume_l if self.volume_l > 1.0 else 0.0

    @property
    def is_empty(self) -> bool:
        return self.volume_l <= 0.5

    def add(self, volume_l: float, brix: float = 0.0) -> float:
        """Adds liquid; anything above capacity overflows and is lost. Returns accepted litres."""
        accepted = max(0.0, min(volume_l, self.capacity_l - self.volume_l))
        self.volume_l += accepted
        self.solids += accepted * brix
        return accepted

    def remove(self, volume_l: float) -> tuple[float, float]:
        """Removes up to volume_l. Returns (litres removed, Brix of what was removed)."""
        removed = max(0.0, min(volume_l, self.volume_l))
        brix = self.brix
        if removed >= self.volume_l:
            self.volume_l, self.solids = 0.0, 0.0
        else:
            self.volume_l -= removed
            self.solids -= removed * brix
        return removed, brix
