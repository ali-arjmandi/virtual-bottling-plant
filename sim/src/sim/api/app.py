"""FastAPI app factory for the simulator API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sim.api import rest_routes, ws_stream
from sim.runtime import SimRuntime


def create_app(runtime: SimRuntime, cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="Delfts Sap Line 1 simulator", version="0.1.0")
    app.state.runtime = runtime
    app.include_router(rest_routes.router)
    app.include_router(ws_stream.router)
    if cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=cors_origins,
                           allow_methods=["*"], allow_headers=["*"])
    return app
