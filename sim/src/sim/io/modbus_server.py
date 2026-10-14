"""Modbus TCP server (MBAP framing) serving the register image to the PLC.

A unit that is 'disconnected' (sensor override) or unknown gets no reply at all, so the PLC sees
a timeout, as with a dead remote I/O station. Every reply refreshes that unit's `{EQ}_Heartbeat`
(a real-time comms counter, not sim time, so it keeps counting while the sim is paused).
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from collections.abc import Callable

from sim.io.modbus_pdu import handle_pdu
from sim.io.register_image import RegisterImage

log = logging.getLogger(__name__)
MBAP = struct.Struct(">HHHB")  # transaction, protocol, length, unit


class ModbusTcpServer:
    def __init__(
        self, image: RegisterImage, disconnected_units: Callable[[], set[int]],
        host: str = "0.0.0.0", port: int = 502,
        monotonic_ms: Callable[[], int] = lambda: int(time.monotonic() * 1000),
    ) -> None:
        self.image = image
        self.disconnected_units = disconnected_units
        self.monotonic_ms = monotonic_ms
        self._heartbeats = {
            unit_id: f"{equipment}_Heartbeat" for unit_id, equipment in image.map.equipment.items()
            if f"{equipment}_Heartbeat" in image.map.signals
        }
        self.host, self.port = host, port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._serve_client, self.host, self.port)
        log.info("Modbus TCP listening on %s:%s", self.host, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    @property
    def bound_port(self) -> int:
        assert self._server is not None
        return int(self._server.sockets[0].getsockname()[1])

    async def _serve_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                header = await reader.readexactly(MBAP.size)
                transaction, protocol, length, unit_id = MBAP.unpack(header)
                pdu = await reader.readexactly(length - 1)
                response = self.respond(unit_id, protocol, pdu)
                if response is not None:
                    writer.write(MBAP.pack(transaction, 0, len(response) + 1, unit_id) + response)
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()

    def respond(self, unit_id: int, protocol: int, pdu: bytes) -> bytes | None:
        """PDU response, or None for no reply."""
        if protocol != 0 or not self.image.has_unit(unit_id):
            return None
        if unit_id in self.disconnected_units():
            return None
        if unit_id in self._heartbeats:
            self.image.set(self._heartbeats[unit_id], (self.monotonic_ms() // 100) & 0xFFFF)
        return handle_pdu(self.image, unit_id, pdu)
