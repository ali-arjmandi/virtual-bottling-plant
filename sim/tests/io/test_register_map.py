import pytest

from sim.io.register_image import RegisterImage
from sim.io.register_map import RegisterMap, Signal


def test_contract_loads_without_overlaps(reg_map: RegisterMap) -> None:
    assert set(reg_map.equipment) == set(range(1, 10))
    assert reg_map.signals["TT202_OutTemp"].unit_id == 2


def test_overlapping_addresses_are_rejected() -> None:
    a = Signal("A", 1, "ir", 0, words=2)
    b = Signal("B", 1, "ir", 1)
    with pytest.raises(ValueError, match="overlaps"):
        RegisterMap([a, b], {1: "X"})


@pytest.mark.parametrize(
    ("name", "value"),
    [("TT202_OutTemp", 85.2), ("AT101_Brix", 11.57), ("F401_Count", 123_456_789),
     ("SIM_TimeMs", 4_000_000_000), ("C501_Jam", True), ("LT301_Level", 0.0)],
)
def test_encode_decode_round_trip(reg_map: RegisterMap, name: str, value: float) -> None:
    image = RegisterImage(reg_map)
    image.set(name, value)
    assert image.get(name) == pytest.approx(value)


def test_32_bit_values_are_high_word_first(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    image.set("F401_Count", 0x0001_0002)
    s = reg_map.signals["F401_Count"]
    assert image.read(s.unit_id, "ir", s.addr, 2) == [1, 2]


def test_words_are_clamped_to_uint16(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    image.set("TT202_OutTemp", -5.0)
    assert image.get("TT202_OutTemp") == 0
    image.set("FT201_Flow", 70_000)
    assert image.get("FT201_Flow") == 0xFFFF
