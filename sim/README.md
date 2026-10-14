# L0 Line Simulator

Physics, failures and operators of Line 1, exposed to the PLC as Modbus TCP remote I/O.
**No control logic lives here**: machines move only when the PLC sets their outputs.
Requirements: [docs/prd/l0-simulator.md](../docs/prd/l0-simulator.md) · Register map:
[contracts/modbus/sim-io.yaml](../contracts/modbus/sim-io.yaml) · API:
[docs/prd/contracts.md §4](../docs/prd/contracts.md).

## Develop

```bash
cd sim
uv sync                                   # or: python -m venv .venv && pip install -e . + dev deps
uv run ruff check src harness tests
uv run mypy src harness
uv run pytest                             # fast suite (~30 s)
uv run pytest -m slow                     # two 24 h acceptance runs (~2 min)
uv run python -m sim                      # serve: Modbus :5020, API :8000, real time
```

## Headless runs (tuning)

Until the PLC exists, `harness/` holds a **stub controller** (just enough start/stop, batching
and steam control to run the line) and a run summary with an OEE estimate and downtime Pareto.
It is test tooling, not the control design, and it is not copied into the Docker image.

```bash
uv run python -m harness.headless_run --hours 24 --seed 42 --out out/
```

Writes `out/events.jsonl` (one sim event per line, identical for the same seed) and
`out/summary.json`. Reference result (seed 42): OEE ≈ 65%, top loss C-501 jams.

## Where to change what

| To change | Edit |
| --- | --- |
| Rates, capacities, tank sizes | `config/line.yaml` |
| Fault frequency and duration | `config/faults.yaml` |
| Shifts, breaks, operator delays | `config/shifts.yaml` |
| Sensor noise and resolution | `config/sensors.yaml` |
| Concentrate lots per product | `config/products.yaml` |
| Signal ↔ register addresses | `../contracts/modbus/sim-io.yaml` + `src/sim/io/plant_bindings.py` |
| Demo timeline | `scenarios/demo.yaml` |
