import struct

from sim.io.modbus_pdu import handle_pdu
from sim.io.register_image import RegisterImage
from sim.io.register_map import RegisterMap


def test_read_input_registers(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    image.set("TT202_OutTemp", 85.2)
    response = handle_pdu(image, 2, struct.pack(">BHH", 4, 0, 2))
    assert response[:2] == bytes([4, 4])
    assert struct.unpack(">2H", response[2:]) == (0, 852)


def test_read_discrete_inputs_packs_bits_lsb_first(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    image.set("C501_Jam", True)  # DI 1 on unit 5
    response = handle_pdu(image, 5, struct.pack(">BHH", 2, 0, 4))
    assert response == bytes([2, 1, 0b0000_0010])


def test_write_single_coil_and_multiple_registers(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    assert handle_pdu(image, 4, struct.pack(">BHH", 5, 0, 0xFF00))[0] == 5
    assert image.get("F401_Run") is True
    pdu = struct.pack(">BHHB2H", 16, 0, 2, 4, 120, 10050)
    assert handle_pdu(image, 4, pdu) == struct.pack(">BHH", 16, 0, 2)
    assert image.get("F401_SpeedSP") == 120
    assert image.get("F401_FillTargetG") == 1005.0


def test_errors_return_exception_codes(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    assert handle_pdu(image, 2, struct.pack(">BHH", 4, 100, 1)) == bytes([0x84, 0x02])
    assert handle_pdu(image, 2, bytes([0x2B])) == bytes([0xAB, 0x01])
    assert handle_pdu(image, 4, struct.pack(">BHH", 5, 0, 0x1234)) == bytes([0x85, 0x03])
