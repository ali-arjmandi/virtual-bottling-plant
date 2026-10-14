"""In-memory process image of all sim units. The plant, the Modbus server and test
controllers all read and write this one image, so the contract is always exercised."""

from __future__ import annotations

from sim.io.register_map import BIT_TYPES, RegisterMap, Signal, SignalType


class RegisterImage:
    def __init__(self, reg_map: RegisterMap) -> None:
        self.map = reg_map
        self._tables: dict[int, dict[str, list[int]]] = {}
        self._slots: dict[str, tuple[list[int], int, Signal]] = {}
        self.clear()

    def clear(self) -> None:
        """Zeroes every register in place (references held by the Modbus server stay valid)."""
        if not self._tables:
            self._tables = {
                unit_id: {t: [0] * self.map.size(unit_id, t) for t in ("di", "coil", "ir", "hr")}
                for unit_id in self.map.equipment
            }
            self._slots = {
                s.name: (self._tables[s.unit_id][s.type], s.addr, s)
                for s in self.map.signals.values()
            }
        for unit in self._tables.values():
            for table in unit.values():
                table[:] = [0] * len(table)

    def has_unit(self, unit_id: int) -> bool:
        return unit_id in self._tables

    # --- engineering access (by signal name) ----------------------------------------------

    def set(self, name: str, value: float | bool) -> None:
        table, addr, s = self._slots[name]
        if s.is_bit:
            table[addr] = 1 if value else 0
        elif s.words == 1:
            raw = int(round(float(value) * s.scale))
            table[addr] = 0 if raw < 0 else (raw if raw < 0xFFFF else 0xFFFF)
        else:
            table[addr : addr + 2] = s.encode(value)

    def get(self, name: str) -> float | bool:
        table, addr, s = self._slots[name]
        return s.decode(table[addr : addr + s.words])

    def get_bool(self, name: str) -> bool:
        return bool(self.get(name))

    def get_float(self, name: str) -> float:
        return float(self.get(name))

    # --- raw access (Modbus server) ---------------------------------------------------------

    def read(self, unit_id: int, type_: SignalType, addr: int, count: int) -> list[int]:
        table = self._tables[unit_id][type_]
        if addr < 0 or count < 1 or addr + count > len(table):
            raise IndexError("illegal data address")
        return table[addr : addr + count]

    def write(self, unit_id: int, type_: SignalType, addr: int, values: list[int]) -> None:
        table = self._tables[unit_id][type_]
        if addr < 0 or addr + len(values) > len(table):
            raise IndexError("illegal data address")
        if type_ in BIT_TYPES:
            values = [1 if v else 0 for v in values]
        table[addr : addr + len(values)] = values
