"""The simulator's REST API (contracts.md §4): the FAT suite's way to create test scenarios."""

from __future__ import annotations

from typing import Any

import httpx


class SimApi:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url, timeout=5)

    def healthy(self) -> bool:
        try:
            return self.http.get("/health").status_code == 200
        except httpx.HTTPError:
            return False

    def state(self) -> dict[str, Any]:
        return self.http.get("/state").raise_for_status().json()

    def reset(self, seed: int = 42, random_faults: bool = False) -> None:
        self.http.post("/reset", json={"seed": seed, "randomFaults": random_faults}).raise_for_status()

    def clock(self, speed: int | None = None, paused: bool | None = None) -> None:
        body = {k: v for k, v in {"speed": speed, "paused": paused}.items() if v is not None}
        self.http.post("/clock", json=body).raise_for_status()

    def fault(self, machine: str, type_: str, duration_s: float | None = None) -> int:
        body: dict[str, Any] = {"machine": machine, "type": type_}
        if duration_s is not None:
            body["durationS"] = duration_s
        return int(self.http.post("/faults", json=body).raise_for_status().json()["id"])

    def override(self, tag: str, mode: str, value: float | None = None) -> None:
        body: dict[str, Any] = {"mode": mode} if value is None else {"mode": mode, "value": value}
        self.http.post(f"/sensors/{tag}/override", json=body).raise_for_status()

    def clear_override(self, tag: str) -> None:
        self.http.delete(f"/sensors/{tag}/override").raise_for_status()

    def clear_all(self) -> None:
        """Removes every active fault and sensor override."""
        state = self.state()
        for fault in state["faults"]:
            self.http.delete(f"/faults/{fault['id']}")
        for tag, sensor in state["sensors"].items():
            if sensor["override"]:
                self.clear_override(tag)
