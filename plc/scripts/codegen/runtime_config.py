"""OpenPLC slave-device config (mbconfig.cfg) and located addresses of the sim I/O.

OpenPLC v3 polls slave devices in file order and packs each register type one device after the
other: discrete inputs → %IX100.0…, coils → %QX100.0…, input registers → %IW100…, holding
registers (write) → %QW100… (ADR 0005). This module is the only place that does that arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass

from codegen.contracts import SimSignal, SimUnit

TYPES = ("di", "coil", "ir", "hr")
AREA = {"di": "IX", "coil": "QX", "ir": "IW", "hr": "QW"}
FIRST_SLAVE_ADDR = 100


@dataclass(frozen=True)
class Located:
    var: str          # local variable name in the IO program (signal name, +_HI/_LO)
    address: str      # %IW104, %IX100.3
    signal: SimSignal
    word: int         # 0 = high (or only) word, 1 = low word

    def csv(self) -> str:
        s = self.signal
        return f"{self.var},{s.unit_id},{s.type},{s.addr + self.word},{self.address}"


def _address(type_: str, index: int) -> str:
    if type_ in ("di", "coil"):
        return f"%{AREA[type_]}{FIRST_SLAVE_ADDR + index // 8}.{index % 8}"
    return f"%{AREA[type_]}{FIRST_SLAVE_ADDR + index}"


def located_addresses(units: list[SimUnit]) -> dict[int, list[Located]]:
    """Per unit id, one entry per register (32-bit signals give _HI and _LO)."""
    offset = dict.fromkeys(TYPES, 0)
    result: dict[int, list[Located]] = {}
    for unit in units:
        rows = []
        for s in sorted(unit.signals, key=lambda s: (TYPES.index(s.type), s.addr)):
            for w in range(s.words):
                var = s.name if s.words == 1 else f"{s.name}_{'HI' if w == 0 else 'LO'}"
                rows.append(Located(var, _address(s.type, offset[s.type] + s.addr + w), s, w))
        result[unit.unit_id] = rows
        for t in TYPES:
            offset[t] += unit.size(t)
    return result


def address_table(units: list[SimUnit]) -> str:
    rows = [r.csv() for unit_rows in located_addresses(units).values() for r in unit_rows]
    return "name,unit,type,register,address\n" + "\n".join(rows) + "\n"


def mbconfig(units: list[SimUnit], polling_ms: int = 50, timeout_ms: int = 250) -> str:
    """@SIM_HOST@ is replaced by plc/runtime/start.sh: libmodbus needs an IP, not a name."""
    out = [f'Num_Devices = "{len(units)}"', f'Polling_Period = "{polling_ms}"',
           f'Timeout = "{timeout_ms}"']
    for i, unit in enumerate(units):
        d = f"device{i}"
        out += [
            f"# --- DEVICE {i}: {unit.equipment} (unit {unit.unit_id}) ---",
            f'{d}.name = "{unit.equipment}"', f'{d}.slave_id = "{unit.unit_id}"',
            f'{d}.protocol = "TCP"', f'{d}.address = "@SIM_HOST@"', f'{d}.IP_Port = "5020"',
            f'{d}.RTU_Baud_Rate = "0"', f'{d}.RTU_Parity = "None"', f'{d}.RTU_Data_Bits = "0"',
            f'{d}.RTU_Stop_Bits = "0"', f'{d}.RTU_TX_Pause = "0"',
            f'{d}.Discrete_Inputs_Start = "0"', f'{d}.Discrete_Inputs_Size = "{unit.size("di")}"',
            f'{d}.Coils_Start = "0"', f'{d}.Coils_Size = "{unit.size("coil")}"',
            f'{d}.Input_Registers_Start = "0"', f'{d}.Input_Registers_Size = "{unit.size("ir")}"',
            f'{d}.Holding_Registers_Read_Start = "0"', f'{d}.Holding_Registers_Read_Size = "0"',
            f'{d}.Holding_Registers_Start = "0"', f'{d}.Holding_Registers_Size = "{unit.size("hr")}"',
        ]
    return "\n".join(out) + "\n"
