from fastapi.testclient import TestClient

from sim.api.app import create_app
from sim.runtime import SimRuntime


def _client(runtime: SimRuntime) -> TestClient:
    return TestClient(create_app(runtime))


def test_fault_via_api_sets_cause_bit(runtime: SimRuntime) -> None:
    client = _client(runtime)
    response = client.post("/faults", json={"machine": "C501", "type": "jam", "durationS": 30})
    assert response.status_code == 201
    runtime.run_for(500)
    assert runtime.image.get_bool("C501_Jam")
    state = client.get("/state").json()
    assert state["faults"][0]["machine"] == "C501"
    assert client.delete(f"/faults/{response.json()['id']}").status_code == 204


def test_unknown_fault_is_404(runtime: SimRuntime) -> None:
    response = _client(runtime).post("/faults", json={"machine": "C501", "type": "nope"})
    assert response.status_code == 404


def test_sensor_override_and_clear(runtime: SimRuntime) -> None:
    client = _client(runtime)
    url = "/sensors/TT202_OutTemp/override"
    assert client.post(url, json={"mode": "disconnect"}).status_code == 204
    assert client.get("/state").json()["disconnectedUnits"] == [2]
    assert client.delete(url).status_code == 204
    assert client.post("/sensors/NOPE/override", json={"mode": "stuck"}).status_code == 404


def test_clock_and_reset(runtime: SimRuntime) -> None:
    client = _client(runtime)
    assert client.post("/clock", json={"speed": 10, "paused": True}).json() == {
        "speed": 10.0, "paused": True}
    assert client.post("/clock", json={"speed": 7}).status_code == 422
    runtime.run_for(5_000)
    assert client.post("/reset", json={"seed": 3}).json() == {"seed": 3, "randomFaults": True}
    assert runtime.t_ms == 0 and runtime.seed == 3
    assert runtime.plant.scheduler.enabled


def test_reset_without_random_faults(runtime: SimRuntime) -> None:
    client = _client(runtime)
    assert client.post("/reset", json={"seed": 1, "randomFaults": False}).status_code == 200
    assert not runtime.plant.scheduler.enabled


def test_drift_and_scenario(runtime: SimRuntime) -> None:
    client = _client(runtime)
    body = {"machine": "F401", "type": "drift", "params": {"nozzle": 7, "rateGPerMin": -2}}
    assert client.post("/faults", json=body).status_code == 201
    assert runtime.plant.filler.weights.drift_rate_g_per_s[6] < 0
    assert client.post("/scenarios/demo/run").status_code == 202
    assert client.post("/scenarios/nope/run").status_code == 404
    runtime.run_for(80_000)
    assert any(e["type"] == "fault_start" and e["data"]["source"] == "scenario"
               for e in client.get("/events").json())
