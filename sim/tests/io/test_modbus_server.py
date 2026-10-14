"""End to end over TCP with a real Modbus client (pymodbus), as the PLC will connect."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pymodbus.client import AsyncModbusTcpClient

from sim.io.modbus_server import ModbusTcpServer
from sim.io.register_image import RegisterImage
from sim.io.register_map import RegisterMap


@pytest.fixture
async def served(reg_map: RegisterMap) -> AsyncIterator[tuple[RegisterImage, set[int], int]]:
    image = RegisterImage(reg_map)
    disconnected: set[int] = set()
    server = ModbusTcpServer(image, lambda: disconnected, host="127.0.0.1", port=0)
    await server.start()
    yield image, disconnected, server.bound_port
    await server.stop()


async def test_client_reads_and_writes(served: tuple[RegisterImage, set[int], int]) -> None:
    image, _, port = served
    image.set("TT202_OutTemp", 84.9)
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1, retries=0)
    await client.connect()
    result = await client.read_input_registers(1, count=1, device_id=2)
    assert result.registers == [849]
    await client.write_coil(0, True, device_id=4)
    assert image.get("F401_Run") is True
    client.close()


async def test_disconnected_unit_does_not_reply(
    served: tuple[RegisterImage, set[int], int],
) -> None:
    _, disconnected, port = served
    disconnected.add(2)
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=0.5, retries=0)
    await client.connect()
    with pytest.raises(Exception):  # noqa: B017 - pymodbus raises its own timeout type
        await client.read_input_registers(1, count=1, device_id=2)
    client.close()


def test_heartbeat_counts_real_time_per_unit(reg_map: RegisterMap) -> None:
    image = RegisterImage(reg_map)
    now = [123_456]
    server = ModbusTcpServer(image, set, monotonic_ms=lambda: now[0])
    read_ir = bytes([0x04, 0, 0, 0, 1])
    server.respond(2, 0, read_ir)
    assert image.get("P201_Heartbeat") == 1234
    assert image.get("F401_Heartbeat") == 0  # only units that answer are refreshed
    now[0] = 65_536 * 100 + 500
    server.respond(2, 0, read_ir)
    assert image.get("P201_Heartbeat") == 5  # wraps at 16 bits


def test_every_unit_has_a_heartbeat(reg_map: RegisterMap) -> None:
    for equipment in reg_map.equipment.values():
        assert f"{equipment}_Heartbeat" in reg_map.signals
