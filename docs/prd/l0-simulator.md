# L0 Line Simulator

Part of the [PRD](../prd.md). Folder: `sim/`. Language: Python 3.12, SimPy, pymodbus, FastAPI.

## Purpose

Stands in for the machines, sensors and actuators of Line 1. It produces realistic data and failures. **It contains no control logic.** Machines move only when the PLC tells them to, as in virtual commissioning.

## Equipment and parameters

| Tag | Equipment | Nominal behaviour | Key signals |
| --- | --- | --- | --- |
| T-101 | Mix tank | 5,000 L batch; fill 20 min, mix 15 min; Brix 11.5 ± 0.3 | Level, Brix, agitator speed, valves |
| P-201 | HTST pasteuriser | SP 85 °C, hold 30 s; < 83 °C needs divert | In/out temp, flow, divert valve |
| T-301 | Buffer tank | 3,000 L | Level |
| F-401 | Filler | 12 nozzles, 120 bpm, 1,005 g ± 3 | Count, speed, nozzle weight, run feedback |
| C-501 | Capper | Torque 2.2 ± 0.15 Nm | Torque, jam, cap hopper level |
| L-601 | Labeler | Roll lasts ~4,000 bottles | Roll status, label error |
| Q-701 | Checkweigher | Reject < 995 g | Per-nozzle subgroup stats, reject count |
| K-801 | Case packer | 6 bottles per case, 20 cases/min | Case count, jam |
| CV | Accumulation conveyors | ~150 bottles between each packaging machine | Fill level, full/empty |

## Requirements

### Physics

| ID | Requirement |
| --- | --- |
| SIM-01 | Tank level from mass balance: dL/dt = (Q_in − Q_out) / A |
| SIM-02 | Pasteuriser outlet temp is first-order plus dead time (τ ≈ 40 s, θ ≈ 5 s), driven by the steam valve output from the PLC |
| SIM-03 | Brix follows the mixing ratio of water, concentrate and sugar |
| SIM-04 | Continuous physics loop at 100 ms sim time; discrete events (bottles, faults, shifts) in SimPy |

### Machines and flow

| ID | Requirement |
| --- | --- |
| SIM-10 | A machine produces only while the PLC run output is on, it has input, and its output conveyor is not full |
| SIM-11 | Conveyors have finite capacity, so a stop spreads upstream (blocked) and downstream (starved) with delay |
| SIM-12 | The sim exposes the *causes* (jam, empty roll, conveyor full). The PLC decides the PackML state |

### Faults

| ID | Requirement |
| --- | --- |
| SIM-20 | Micro-stops: Poisson process, 10 to 60 s |
| SIM-21 | Breakdowns: Weibull time between failures, lognormal repair time of 5 to 45 min |
| SIM-22 | Material shortages: label roll, cap hopper |
| SIM-23 | Parameters per machine in `sim/config/faults.yaml` (start values below) |

| Machine | Fault | Frequency | Duration |
| --- | --- | --- | --- |
| C-501 | Cap jam | ~every 8 min | 10–60 s |
| F-401 | Nozzle leak | ~every 3 days | 20–40 min |
| L-601 | Roll empty | every ~4,000 bottles | 2–5 min |
| L-601 | Label glue | ~every 20 min | 15–90 s |
| K-801 | Case jam | ~every 40 min | 1–5 min |
| P-201 | Steam pressure drop | ~weekly | 10–30 min, causes divert |

### Quality

| ID | Requirement |
| --- | --- |
| SIM-30 | Fill weight per nozzle is normal (σ ≈ 1 g) |
| SIM-31 | One nozzle drifts slowly (~0.05 g/h) until SPC catches it. It can also be triggered from the API |
| SIM-32 | Some batches come out of Brix spec (rate set in config) |

### Sensors

| ID | Requirement |
| --- | --- |
| SIM-40 | Gaussian noise and quantisation per sensor (e.g. 0.1 °C) |
| SIM-41 | Failure modes: stuck value, disconnect (no Modbus answer for that unit) |
| SIM-42 | The sim keeps both the true and the reported value; `/state` returns both |

### Human operations

| ID | Requirement |
| --- | --- |
| SIM-50 | Shift calendar and planned breaks in `sim/config/shifts.yaml` |
| SIM-51 | Operator response time to a stop depends on the shift (evening shift a bit slower) |
| SIM-52 | Product change triggers a 45-minute CIP |

### Control and repeatability

| ID | Requirement |
| --- | --- |
| SIM-60 | Fixed seed gives an identical run (all randomness from one seeded generator per subsystem) |
| SIM-61 | Time speed 1×, 10×, 60×, plus pause |
| SIM-62 | Modbus map loaded from `contracts/modbus/sim-io.yaml` |
| SIM-63 | REST + WebSocket API as in [contracts.md §4](contracts.md) |
| SIM-64 | Scenario files (`sim/scenarios/*.yaml`) schedule faults at sim times. `demo.yaml` drives the video |
| SIM-65 | Headless mode for long runs: writes a summary (counts, stops, OEE estimate) for tuning |

## Folder structure

```
sim/
├── pyproject.toml
├── Dockerfile
├── config/                 # faults.yaml, shifts.yaml, sensors.yaml, products.yaml
├── scenarios/              # demo.yaml, ...
├── src/sim/
│   ├── main.py             # wires everything, starts loop + servers
│   ├── clock.py            # sim time, speed, pause
│   ├── rng.py              # seeded generators per subsystem
│   ├── physics/            # tank.py, pasteurizer.py, mixing.py
│   ├── machines/           # filler.py, capper.py, labeler.py, checkweigher.py, case_packer.py
│   ├── flow/               # conveyor.py, line.py
│   ├── faults/             # distributions.py, fault_scheduler.py, fault_catalog.py
│   ├── sensors/            # sensor.py, sensor_faults.py
│   ├── operations/         # shift_calendar.py, operator.py
│   ├── io/                 # register_map.py, modbus_server.py
│   ├── api/                # rest_routes.py, ws_stream.py
│   └── scenarios/          # scenario_runner.py
└── tests/                  # mirrors src/sim/
```

## Acceptance criteria

- [ ] A 24 h headless run with the reference fault set gives OEE of 55–70% (in P1, a minimal Python PLC stub in `sim/tests/` drives the run; the real sim has no control logic)
- [ ] The downtime Pareto from that run has one clear top reason (expected: C-501 jams)
- [ ] Two runs with the same seed give byte-identical event logs
- [ ] Stopping C-501 blocks F-401 once the conveyor is full, and starves L-601 onwards
- [ ] Unit tests cover physics models and fault distributions (mean within 5% of config)
