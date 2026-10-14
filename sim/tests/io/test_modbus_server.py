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
