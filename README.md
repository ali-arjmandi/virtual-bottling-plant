# Virtual Bottling Plant · Delfts Sap B.V., Line 1

An end-to-end PLC → SCADA → MES system for a simulated juice bottling line. A physics-based
simulator stands in for the machines, an OpenPLC soft-PLC runs IEC 61131-3 Structured Text with
PackML state machines, Ignition provides an ISA-101 HMI, and a TypeScript MES handles work orders,
recipes, OEE and lot genealogy over an MQTT Unified Namespace with Sparkplug B.

> **Status: Phase 1 of 6 done (L0 simulator).** See [docs/prd.md](docs/prd.md) for the plan.

## What runs today

The L0 simulator: Line 1 physics, failures and operators, served to the PLC as Modbus TCP remote
I/O, plus a REST/WebSocket API for fault injection.

```bash
docker compose up --build          # sim API on 127.0.0.1:8000, Modbus TCP on 127.0.0.1:5020
curl -X POST 127.0.0.1:8000/faults -H 'content-type: application/json' \
     -d '{"machine":"C501","type":"jam","durationS":30}'
curl 127.0.0.1:8000/state
```

`docker compose -f docker-compose.yml up` runs without the dev port mappings, closer to the
Purdue zoning in [docs/prd/architecture.md](docs/prd/architecture.md).

## Repo map

| Folder | Layer | Status |
| --- | --- | --- |
| [sim/](sim/) | L0 simulator (Python) | done |
| [contracts/](contracts/) | Interfaces between layers | sim ↔ PLC map |
| `plc/` | L1 OpenPLC, Structured Text | Phase 2 |
| `services/edge-bridge/` | Modbus → MQTT / Sparkplug B | Phase 3 |
| `scada/` | Ignition Perspective HMI | Phase 4 |
| `services/mes-api/`, `apps/mes-web/` | MES | Phase 5 |
| [docs/](docs/) | PRD, ADRs | |

## Honest scope

This project does not replace real commissioning experience: wiring, physical I/O, Profinet and
work at the machine. It shows the logic, integration and data side end to end.
