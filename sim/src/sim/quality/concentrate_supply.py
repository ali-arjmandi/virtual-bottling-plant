"""Concentrate lots per product. Each lot has its own Brix; a few are out of tolerance (SIM-32)."""

from __future__ import annotations

import numpy as np

from sim.config_models import ProductsConfig, ProductSpec
from sim.event_log import EventLog


class ConcentrateLot:
    def __init__(self, lot_no: int, brix: float, volume_l: float) -> None:
        self.lot_no = lot_no
        self.brix = brix
        self.remaining_l = volume_l


class ConcentrateSupply:
    def __init__(self, config: ProductsConfig, rng: np.random.Generator, log: EventLog) -> None:
        self._specs = {spec.select_code: (name, spec) for name, spec in config.products.items()}
        self._rng = rng
        self._log = log
        self._lots: dict[int, ConcentrateLot] = {}

    def is_known(self, select_code: int) -> bool:
        return select_code in self._specs

    def current_lot(self, select_code: int, t_ms: int) -> ConcentrateLot | None:
        if select_code not in self._specs:
            return None
        lot = self._lots.get(select_code)
        if lot is None or lot.remaining_l <= 0:
            lot = self._new_lot(select_code, lot, t_ms)
        return lot

    def draw(self, select_code: int, volume_l: float, t_ms: int) -> float:
        """Consumes concentrate and returns its Brix (0 if no product is selected)."""
        lot = self.current_lot(select_code, t_ms)
        if lot is None:
            return 0.0
        lot.remaining_l -= volume_l
        return lot.brix

    def _new_lot(self, code: int, previous: ConcentrateLot | None, t_ms: int) -> ConcentrateLot:
        name, spec = self._specs[code]
        lot_no = previous.lot_no + 1 if previous else spec.first_lot_no
        lot = ConcentrateLot(lot_no, self._draw_brix(spec), spec.lot_volume_l)
        self._lots[code] = lot
        self._log.emit(t_ms, "conc_lot_changed", "T101", product=name, lot_no=lot_no,
                       brix=lot.brix)
        return lot

    def _draw_brix(self, spec: ProductSpec) -> float:
        brix = float(self._rng.normal(spec.concentrate_brix, spec.lot_brix_sd))
        if self._rng.random() < spec.offspec_lot_probability:
            brix += spec.offspec_brix_delta * float(self._rng.choice([-1.0, 1.0]))
        return brix
