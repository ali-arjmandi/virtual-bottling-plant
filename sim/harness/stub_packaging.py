"""Harness only, NOT the real PLC logic: just enough packaging control to run the line in
Phase 1. Latches the panel buttons, holds a machine while a stop cause is present, releases it
on reset."""

from __future__ import annotations

from sim.io.register_image import RegisterImage

SPEEDS = {"F401": 120, "C501": 130, "L601": 130, "Q701": 140, "K801": 22}
CAUSES = {
    "F401": ("F401_NozzleLeak",),
    "C501": ("C501_Jam", "C501_Breakdown", "LSL502_CapsEmpty"),
    "L601": ("L601_RollEmpty", "L601_LabelError", "L601_Breakdown"),
    "Q701": (),
    "K801": ("K801_Jam", "K801_Breakdown"),
}


class StubPackaging:
    def __init__(self, image: RegisterImage) -> None:
        self.img = image
        self.line_on = False
        self.held: set[str] = set()

    def step(self) -> None:
        g = self.img.get_bool
        if g("PB_Start"):
            self.line_on = True
        if g("PB_Stop"):
            self.line_on = False
        for machine, causes in CAUSES.items():
            if any(g(c) for c in causes):
                self.held.add(machine)
            elif g("PB_Reset"):
                self.held.discard(machine)
        for machine, speed in SPEEDS.items():
            self.img.set(f"{machine}_Run", self.line_on and machine not in self.held)
            self.img.set(f"{machine}_SpeedSP", speed)
        self.img.set("F401_FillTargetG", 1005.0)
        self.img.set("Q701_RejectLimitG", 995.0)
