"""Serve mode: real-time sim + Modbus TCP server + REST/WS API in one asyncio loop."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn

from sim.api.app import create_app
from sim.config_models import load_config
from sim.io.modbus_server import ModbusTcpServer
from sim.io.register_map import DEFAULT_MAP_PATH, RegisterMap
from sim.runtime import SimRuntime

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True)
class Settings:
    seed: int
    speed: float
    modbus_port: int
    api_port: int
    config_dir: Path
    io_map: Path
    cors_origins: list[str]

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ.get
        return cls(
            seed=int(env("SIM_SEED", "42")),
            speed=float(env("SIM_SPEED", "1")),
            modbus_port=int(env("SIM_MODBUS_PORT", "5020")),
            api_port=int(env("SIM_API_PORT", "8000")),
            config_dir=Path(env("SIM_CONFIG_DIR", str(DEFAULT_CONFIG_DIR))),
            io_map=Path(env("SIM_IO_MAP", str(DEFAULT_MAP_PATH))),
            cors_origins=[o for o in env("SIM_CORS_ORIGINS", "").split(",") if o],
        )


async def serve(settings: Settings) -> None:
    runtime = SimRuntime(load_config(settings.config_dir), RegisterMap.load(settings.io_map),
                         settings.seed)
    runtime.clock.set_speed(settings.speed)
    modbus = ModbusTcpServer(runtime.image, runtime.disconnected_units,
                             port=settings.modbus_port)
    await modbus.start()
    api = uvicorn.Server(uvicorn.Config(create_app(runtime, settings.cors_origins),
                                        host="0.0.0.0", port=settings.api_port))
    sim_task = asyncio.create_task(runtime.run_realtime())
    try:
        await api.serve()
    finally:
        sim_task.cancel()
        await modbus.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(serve(Settings.from_env()))
