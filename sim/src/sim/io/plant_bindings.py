"""The only place that knows which model attribute maps to which register (like the wiring
list of a real remote I/O panel). Models never touch the register image."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sim.io.register_image import RegisterImage

if TYPE_CHECKING:
    from sim.plant import Plant

UINT32 = 1 << 32


class PlantBindings:
    def __init__(self, plant: Plant, image: RegisterImage) -> None:
        self.p = plant
        self.img = image
        self._fault_signals = [
            (machine, spec.signal)
            for machine in plant.catalog.machines()
            for spec in plant.catalog.for_machine(machine)
            if spec.signal and machine in plant.machines
        ]
        self._subgroup_seq = [-1] * len(plant.checkweigher.subgroups)

    def read_outputs(self) -> None:
        """PLC → sim: coils and holding registers."""
        g, p = self.img.get, self.p
        mt = p.mix_tank
        mt.water_open, mt.conc_open = bool(g("XV101_Water")), bool(g("XV102_Conc"))
        mt.sugar_open, mt.agitator_on = bool(g("XV103_Sugar")), bool(g("M101_Agitator"))
        mt.pump_on, mt.drain_open = bool(g("P101_TransferPump")), bool(g("XV109_Drain"))
        mt.conc_select = int(g("T101_ConcSelect"))
        p.cip.run_cmd = bool(g("T101_CipRun"))
        p.pasteurizer.steam_valve_pct = float(g("TCV201_SteamValve"))
        p.pasteurizer.divert_cmd = bool(g("XV203_Divert"))
        p.buffer.drain_open = bool(g("XV309_Drain"))
        for name, machine in p.machines.items():
            machine.run_cmd = bool(g(f"{name}_Run"))
            if name != "K801":
                machine.speed_sp = float(g(f"{name}_SpeedSP"))
        p.case_packer.speed_sp_cpm = float(g("K801_SpeedSP"))
        p.filler.fill_target_g = float(g("F401_FillTargetG"))
        p.checkweigher.reject_limit_g = float(g("Q701_RejectLimitG"))

    def write_inputs(self, t_ms: int) -> None:
        """Sim → PLC: discrete inputs and input registers."""
        self._write_process()
        self._write_machines()
        self._write_line(t_ms)

    def _write_process(self) -> None:
        s, r, p = self.img.set, self.p.sensors.read, self.p
        mt, px = p.mix_tank, p.pasteurizer
        s("LT101_Level", r("LT101_Level", mt.tank.level_pct))
        s("AT101_Brix", r("AT101_Brix", mt.probe_brix))
        s("FT101_WaterFlow", r("FT101_WaterFlow", mt.water_flow))
        s("FT102_ConcFlow", r("FT102_ConcFlow", mt.conc_flow))
        s("FT103_SugarFlow", r("FT103_SugarFlow", mt.sugar_flow))
        rpm = mt.cfg.agitator_rpm if mt.agitator_on else 0.0
        s("ST101_AgitatorRpm", r("ST101_AgitatorRpm", rpm))
        s("T101_ConcLotNo", mt.lot_no)
        s("LSL101_Empty", mt.tank.is_empty)
        s("M101_Running", mt.agitator_on)
        s("T101_CipDone", p.cip.done)
        s("TT201_InTemp", r("TT201_InTemp", px.inlet_c))
        s("TT202_OutTemp", r("TT202_OutTemp", px.outlet_c))
        s("FT201_Flow", r("FT201_Flow", px.flow_lpm))
        s("PT201_SteamPressure", r("PT201_SteamPressure", px.steam_pressure_bar))
        s("ZS203_DivertOpen", px.divert_open)
        s("LT301_Level", r("LT301_Level", p.buffer.tank.level_pct))
        s("LSL301_Low", p.buffer.suction_low)

    def _write_machines(self) -> None:
        s, r, p = self.img.set, self.p.sensors.read, self.p
        for name, machine in p.machines.items():
            s(f"{name}_Running", machine.running)
            if name != "K801":
                s(f"{name}_Speed", machine.speed)
                s(f"{name}_Count", machine.cycles % UINT32)
        for machine_name, signal in self._fault_signals:
            s(signal, p.machines[machine_name].fault_signal_active(signal))
        s("C501_Torque", r("C501_Torque", p.capper.torque_nm))
        s("LT502_CapHopper", r("LT502_CapHopper", p.hopper.level_pct))
        s("LSL502_CapsEmpty", p.hopper.empty)
        s("L601_RollRemaining", p.scheduler.remaining("L601", "roll_empty"))
        cw = p.checkweigher
        s("Q701_RejectCount", cw.reject_count % UINT32)
        s("WT701_LastWeight", cw.last_weight_g)
        for i, group in enumerate(cw.subgroups, start=1):
            if self._subgroup_seq[i - 1] == group.seq:
                continue
            self._subgroup_seq[i - 1] = group.seq
            s(f"Q701_N{i:02d}_Seq", group.seq)
            s(f"Q701_N{i:02d}_Mean", group.mean_g)
            s(f"Q701_N{i:02d}_Range", group.range_g)
        s("K801_Speed", p.case_packer.speed_cpm)
        s("K801_CaseCount", p.case_packer.case_count % UINT32)

    def _write_line(self, t_ms: int) -> None:
        s, p = self.img.set, self.p
        s("SIM_TimeMs", t_ms % UINT32)
        for name, conveyor in p.conveyors.items():
            s(f"{name}_Fill", conveyor.fill)
            s(f"{name}_Full", conveyor.full)
        panel = p.operator.panel
        s("PB_Start", panel.start)
        s("PB_Stop", panel.stop)
        s("PB_Reset", panel.reset)
