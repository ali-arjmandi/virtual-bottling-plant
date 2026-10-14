"""Modbus application layer (PDU) on top of the register image. Pure functions, no I/O.

Supported: FC1/2/3/4 reads, FC5/6 single writes, FC15/16 multiple writes.
Writes are only accepted for PLC outputs (coils, holding registers), as on real remote I/O.
"""

from __future__ import annotations

import struct

from sim.io.register_image import RegisterImage
from sim.io.register_map import SignalType

ILLEGAL_FUNCTION, ILLEGAL_ADDRESS, ILLEGAL_VALUE = 0x01, 0x02, 0x03
MAX_READ_BITS, MAX_READ_WORDS = 2000, 125

READS: dict[int, SignalType] = {1: "coil", 2: "di", 3: "hr", 4: "ir"}


def _exception(function: int, code: int) -> bytes:
    return bytes([function | 0x80, code])


def _pack_bits(bits: list[int]) -> bytes:
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def _unpack_bits(data: bytes, count: int) -> list[int]:
    return [(data[i // 8] >> (i % 8)) & 1 for i in range(count)]


def handle_pdu(image: RegisterImage, unit_id: int, pdu: bytes) -> bytes:
    if not pdu:
        return _exception(0, ILLEGAL_FUNCTION)
    function = pdu[0]
    try:
        if function in READS:
            return _read(image, unit_id, function, pdu)
        if function in (5, 6):
            return _write_single(image, unit_id, function, pdu)
        if function in (15, 16):
            return _write_multiple(image, unit_id, function, pdu)
    except IndexError:
        return _exception(function, ILLEGAL_ADDRESS)
    except (ValueError, struct.error):
        return _exception(function, ILLEGAL_VALUE)
    return _exception(function, ILLEGAL_FUNCTION)


def _read(image: RegisterImage, unit_id: int, function: int, pdu: bytes) -> bytes:
    addr, count = struct.unpack(">HH", pdu[1:5])
    type_ = READS[function]
    limit = MAX_READ_BITS if function in (1, 2) else MAX_READ_WORDS
    if not 1 <= count <= limit:
        raise ValueError("bad quantity")
    values = image.read(unit_id, type_, addr, count)
    data = _pack_bits(values) if function in (1, 2) else struct.pack(f">{count}H", *values)
    return bytes([function, len(data)]) + data


def _write_single(image: RegisterImage, unit_id: int, function: int, pdu: bytes) -> bytes:
    addr, value = struct.unpack(">HH", pdu[1:5])
    if function == 5:
        if value not in (0x0000, 0xFF00):
            raise ValueError("coil value must be 0x0000 or 0xFF00")
        image.write(unit_id, "coil", addr, [1 if value else 0])
    else:
        image.write(unit_id, "hr", addr, [value])
    return pdu[:5]


def _write_multiple(image: RegisterImage, unit_id: int, function: int, pdu: bytes) -> bytes:
    addr, count, byte_count = struct.unpack(">HHB", pdu[1:6])
    data = pdu[6 : 6 + byte_count]
    if function == 15:
        if byte_count != (count + 7) // 8 or len(data) != byte_count:
            raise ValueError("bad byte count")
        image.write(unit_id, "coil", addr, _unpack_bits(data, count))
    else:
        if byte_count != 2 * count or len(data) != byte_count:
            raise ValueError("bad byte count")
        image.write(unit_id, "hr", addr, list(struct.unpack(f">{count}H", data)))
    return bytes([function]) + struct.pack(">HH", addr, count)
