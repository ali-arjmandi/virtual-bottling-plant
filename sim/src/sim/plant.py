"""Line 1 as a whole: builds every unit and advances them one tick at a time (SIM-04).

Tick order: read PLC outputs → process → packaging (downstream first) → faults → publish
sensors → after-tick hooks (test controllers).
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any

import simpy

from sim.config_models import SimConfig
from sim.event_log import EventLog
from sim.faults.fault_catalog import FaultCatalog
from sim.faults.fault_injector import FaultInjector
from sim.faults.fault_scheduler import FaultScheduler
from sim.faults.fault_target import FaultTarget
from sim.flow.conveyor import Conveyor
from sim.io.plant_bindings import PlantBindings
from sim.io.register_image import RegisterImage
from sim.machines.base_machine import Machine
from sim.machines.cap_hopper import CapHopper
from sim.machines.capper import Capper
from sim.machines.case_packer import CasePacker
from sim.machines.checkweigher import Checkweigher
from sim.machines.filler import Filler
from sim.machines.labeler import Labeler
from sim.machines.machine_status import StatusTracker
from sim.operations.operator import Operator
from sim.operations.shift_calendar import ShiftCalendar
from sim.process.buffer_tank import BufferTank
from sim.process.cip_skid import CipSkid
from sim.process.mix_tank import MixTank
from sim.process.pasteurizer import Pasteurizer
from sim.quality.concentrate_supply import ConcentrateSupply
from sim.rng import NoiseBuffer, RngFactory
from sim.sensors.sensor_bank import SensorBank


class Plant:
    def __init__(
        self, env: simpy.Environment, cfg: SimConfig, image: RegisterImage, log: EventLog,
        rngs: RngFactory,
    ) -> None:
        line = cfg.line
        self.env, self.cfg, self.log = env, cfg, log
        self.tick_ms = line.tick_ms
        self.tick_s = line.tick_ms / 1000.0
        self.start = datetime.fromisoformat(line.start_time)
        self.calendar = ShiftCalendar(cfg.shifts, self.start)

        supply = ConcentrateSupply(cfg.products, rngs.stream("concentrate"), log)
        self.mix_tank = MixTank(line.mix_tank, supply, cfg.products.sugar_syrup_brix)
        self.pasteurizer = Pasteurizer(line.pasteurizer, self.tick_s, line.mix_tank.product_temp_c)
        self.buffer = BufferTank(line.buffer_tank)
        self.cip = CipSkid(line.cip.duration_s, log)

        self.conveyors = {name: Conveyor(name, cap) for name, cap in line.conveyors.items()}
        cv = self.conveyors
        debounce_ms = int(line.status_debounce_s * 1000)

        def tracker(name: str) -> StatusTracker:
            return StatusTracker(name, log, debounce_ms)

        self.hopper = CapHopper(line.capper, rngs.stream("cap_hopper"), log)
        self.filler = Filler(line.filler, tracker("F401"), self.buffer, cv["CV1"],
                             rngs.stream("filler"))
        self.capper = Capper(line.capper, tracker("C501"), cv["CV1"], cv["CV2"], self.hopper,
                             NoiseBuffer(rngs.stream("capper")))
        self.labeler = Labeler(line.labeler, tracker("L601"), cv["CV2"], cv["CV3"])
        self.checkweigher = Checkweigher(line.checkweigher, line.filler.nozzles, tracker("Q701"),
                                         cv["CV3"], cv["CV4"], NoiseBuffer(rngs.stream("scale")))
        self.case_packer = CasePacker(line.case_packer, tracker("K801"), cv["CV4"])
        self.machines: dict[str, Machine] = {
            m.name: m for m in (self.filler, self.capper, self.labeler, self.checkweigher,
                                self.case_packer)
        }

        self.sensors = SensorBank(cfg.sensors, image.map, rngs, log)
        self.operator = Operator(env, cfg.shifts.operator, self.calendar,
                                 rngs.stream("operator"), log)
        targets: dict[str, FaultTarget] = {**self.machines, "P201": self.pasteurizer}
        self.catalog = FaultCatalog(cfg.faults)
        self.injector = FaultInjector(env, log, self.catalog, targets,
                                      rngs.stream("fault/durations"),
                                      self.calendar.response_factor)
        self.injector.on_cleared.append(self.operator.on_fault_cleared)
        self.scheduler = FaultScheduler(self.injector, rngs)
        self.bindings = PlantBindings(self, image)
        self.after_tick: list[Callable[[int], None]] = []
        env.process(self._run())

    def _run(self) -> Generator[Any, Any, None]:
        while True:
            self.tick(int(self.env.now))
            yield self.env.timeout(self.tick_ms)

    def tick(self, t_ms: int) -> None:
        dt = self.tick_s
        self.bindings.read_outputs()

        self.cip.step(dt, t_ms)
        volume, brix = self.mix_tank.step(dt, t_ms, self.cfg.line.pasteurizer.transfer_flow_lpm)
        self.pasteurizer.step(dt, volume)
        if self.pasteurizer.divert_open:
            self.mix_tank.receive_return(volume, brix)
        else:
            self.buffer.receive(volume, brix)
        self.buffer.step(dt)

        for machine in reversed(list(self.machines.values())):
            machine.step(dt, t_ms)
        if self.hopper.step(t_ms, self.calendar.response_factor(t_ms)):
            self.operator.on_condition_cleared()
        self.scheduler.step()

        self.bindings.write_inputs(t_ms)
        for hook in self.after_tick:
            hook(t_ms)
