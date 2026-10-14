"""Harness only, NOT the real PLC logic: batch sequence for T-101, a PI loop on P-201 with a
simple divert, and drain + CIP on a product change."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from enum import StrEnum
from typing import Any

from sim.io.register_image import RegisterImage

PRODUCT_CODES = {"orange": 1, "apple": 2}
CONC_BRIX = {"orange": 65.0, "apple": 70.0}
SUGAR_BRIX = 67.0
NOMINAL_LPM, RECIRC_LPM, FF_PCT_AT_NOMINAL = 400.0, 50.0, 60.0


class Step(StrEnum):
    IDLE = "idle"
    FILL = "fill"
    MIX = "mix"
    TRANSFER = "transfer"
    DRAIN = "drain"
    CIP = "cip"


class StubProcess:
    def __init__(self, image: RegisterImage, plan: dict[str, Any], start: datetime) -> None:
        self.img = image
        self.plan = plan
        self.start = start
        self.step_ = Step.IDLE
        self.product = plan["default"]
        self._dosed = {"water": 0.0, "conc": 0.0, "sugar": 0.0}
        self._targets = self._batch_targets(self.product)
        self._mix_since = 0
        self._integral = 0.0
        self._last_ms = 0

    def step(self, t_ms: int) -> None:
        dt_s = (t_ms - self._last_ms) / 1000.0
        self._last_ms = t_ms
        now = self.start + timedelta(milliseconds=t_ms)
        self._sequence(now, t_ms, dt_s)
        self._pasteurizer(dt_s)
        self.img.set("T101_ConcSelect", PRODUCT_CODES[self.product])

    # --- T-101 sequence ---------------------------------------------------------------------

    def _sequence(self, now: datetime, t_ms: int, dt_s: float) -> None:
        g, s = self.img.get_float, self.img.set
        wanted = self.plan["weekdays"].get(now.weekday(), self.plan["default"])
        if self.step_ == Step.IDLE and wanted != self.product and self._window_open(now):
            self.step_ = Step.DRAIN
        if self.step_ == Step.DRAIN:
            empty = self.img.get_bool("LSL101_Empty") and g("LT301_Level") < 0.5
            s("XV109_Drain", not empty)
            s("XV309_Drain", not empty)
            if empty:
                self.step_ = Step.CIP
        elif self.step_ == Step.CIP:
            s("T101_CipRun", True)
            if self.img.get_bool("T101_CipDone"):
                s("T101_CipRun", False)
                self.product, self._targets = wanted, self._batch_targets(wanted)
                self.step_ = Step.IDLE
        elif self.step_ == Step.IDLE:
            if self._window_open(now) and self.img.get_bool("LSL101_Empty"):
                self._dosed = dict.fromkeys(self._dosed, 0.0)
                self.step_ = Step.FILL
        elif self.step_ == Step.FILL:
            self._fill(dt_s, t_ms)
        elif self.step_ == Step.MIX:
            if t_ms - self._mix_since >= self.plan["batch"]["mix_minutes"] * 60_000:
                self.step_ = Step.TRANSFER
        elif self.step_ == Step.TRANSFER:
            level = g("LT301_Level")
            if level < 90:
                s("P101_TransferPump", True)
            elif level > 98:
                s("P101_TransferPump", False)
            if self.img.get_bool("LSL101_Empty"):
                s("P101_TransferPump", False)
                self.step_ = Step.IDLE
        s("M101_Agitator", self.step_ in (Step.MIX, Step.TRANSFER))

    def _fill(self, dt_s: float, t_ms: int) -> None:
        flows = {"water": "FT101_WaterFlow", "conc": "FT102_ConcFlow", "sugar": "FT103_SugarFlow"}
        valves = {"water": "XV101_Water", "conc": "XV102_Conc", "sugar": "XV103_Sugar"}
        done = True
        for key, tag in flows.items():
            self._dosed[key] += self.img.get_float(tag) * dt_s / 60.0
            open_ = self._dosed[key] < self._targets[key]
            self.img.set(valves[key], open_)
            done = done and not open_
        if done:
            self.step_, self._mix_since = Step.MIX, t_ms

    def _window_open(self, now: datetime) -> bool:
        batch = self.plan["batch"]
        lo, hi = (time.fromisoformat(batch[k]) for k in ("allowed_from", "allowed_until"))
        return now.weekday() in self.plan["weekdays"] and lo <= now.time() < hi

    def _batch_targets(self, product: str) -> dict[str, float]:
        batch = self.plan["batch"]
        volume, sugar_bx = batch["volume_l"], batch["sugar_brix_share"]
        sugar = sugar_bx * volume / SUGAR_BRIX
        conc = (batch["target_brix"] - sugar_bx) * volume / CONC_BRIX[product]
        return {"water": volume - sugar - conc, "conc": conc, "sugar": sugar}

    # --- P-201 ------------------------------------------------------------------------------

    def _pasteurizer(self, dt_s: float) -> None:
        """PI with flow feedforward: steam demand scales with product flow."""
        temp = self.img.get_float("TT202_OutTemp")
        flow = max(self.img.get_float("FT201_Flow"), RECIRC_LPM)
        feedforward = FF_PCT_AT_NOMINAL * flow / NOMINAL_LPM
        error = 85.0 - temp
        self._integral = min(max(self._integral + 2.0 * error * dt_s / 60.0, -50.0), 50.0)
        valve = feedforward + 2.0 * error + self._integral
        self.img.set("TCV201_SteamValve", min(max(valve, 0.0), 100.0))
        if temp < 83.0:
            self.img.set("XV203_Divert", True)
        elif temp > 85.0:
            self.img.set("XV203_Divert", False)
