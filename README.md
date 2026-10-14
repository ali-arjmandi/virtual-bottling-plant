# Virtual Bottling Plant · Delfts Sap B.V., Line 1

An end-to-end PLC → SCADA → MES system for a simulated juice bottling line. A physics-based
simulator stands in for the machines, an OpenPLC soft-PLC runs IEC 61131-3 Structured Text with
PackML state machines, Ignition provides an ISA-101 HMI, and a TypeScript MES handles work orders,
recipes, OEE and lot genealogy over an MQTT Unified Namespace with Sparkplug B.

> **Status: Phase 2 of 6 done (L0 simulator, L1 PLC).** See [docs/prd.md](docs/prd.md) for the plan.

## What runs today

The L0 simulator (Line 1 physics, failures and operators, served as Modbus TCP remote I/O) and
the L1 soft-PLC that controls it: PackML machines, the T-101 batch, the P-201 pasteuriser PID
with divert, alarms with first-out, and the recipe handshake, with a FAT suite in CI.

```bash
docker compose up --build          # sim API :8000, PLC Modbus :5502, OpenPLC UI :8080 (localhost)
curl -X POST 127.0.0.1:8000/faults -H 'content-type: application/json' \
     -d '{"machine":"C501","type":"jam","durationS":30}'      # capper Held, filler blocked...
pip install -r tests/fat/requirements.txt && python -m pytest tests/fat -v   # PLC FAT suite
```

`docker compose -f docker-compose.yml up` runs without the dev port mappings, closer to the
Purdue zoning in [docs/prd/architecture.md](docs/prd/architecture.md).

## Repo map

| Folder | Layer | Status |
| --- | --- | --- |
| [sim/](sim/) | L0 simulator (Python) | done |
| [contracts/](contracts/) | Interfaces between layers | sim ↔ PLC, PLC ↔ bridge maps |
| [plc/](plc/) | L1 OpenPLC, Structured Text | done |
| [tests/fat/](tests/fat/) | PLC factory acceptance tests | done |
| `services/edge-bridge/` | Modbus → MQTT / Sparkplug B | Phase 3 |
| `scada/` | Ignition Perspective HMI | Phase 4 |
| `services/mes-api/`, `apps/mes-web/` | MES | Phase 5 |
| [docs/](docs/) | PRD, ADRs | |

## Next steps (a real plant)

- A second mix tank (T-102) so batching never limits the line (one tank has ~30% headroom).

## Honest scope

This project does not replace real commissioning experience: wiring, physical I/O, Profinet and
work at the machine. It shows the logic, integration and data side end to end.
