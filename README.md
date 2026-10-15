# Virtual Bottling Plant · Delfts Sap B.V., Line 1

An end-to-end PLC → SCADA → MES system for a simulated juice bottling line. A physics-based
simulator stands in for the machines, an OpenPLC soft-PLC runs IEC 61131-3 Structured Text with
PackML state machines, Ignition provides an ISA-101 HMI, and a TypeScript MES handles work orders,
recipes, OEE and lot genealogy over an MQTT Unified Namespace with Sparkplug B.

> **Status: Phase 3 of 6 done (L0 simulator, L1 PLC, L1/L2 edge bridge + Unified Namespace); Phase 4 (Ignition HMI) in progress.** See [docs/prd.md](docs/prd.md) for the plan.

## What runs today

The L0 simulator (Line 1 physics, failures and operators, served as Modbus TCP remote I/O),
the L1 soft-PLC that controls it (PackML machines, the T-101 batch, the P-201 pasteuriser PID
with divert, alarms with first-out, the recipe handshake), and the edge bridge that is the
PLC's only client: it publishes Line 1 to an EMQX Unified Namespace as Sparkplug B telemetry
and ISA-95 JSON events, and takes HMI commands and MES recipe downloads back to the PLC.

```bash
cp .env.example .env               # broker passwords (change them), sim seed and speed
docker compose up --build          # sim :8000, PLC Modbus :5502, OpenPLC UI :8080,
                                   # MQTT TLS :8883 (CA: infra/certs/out/ca.crt), EMQX UI :18083
curl -X POST 127.0.0.1:8000/faults -H 'content-type: application/json' \
     -d '{"machine":"C501","type":"jam","durationS":30}'      # capper Held, filler blocked...
pip install -r tests/fat/requirements.txt && python -m pytest tests/fat -v   # PLC FAT suite
corepack enable && pnpm install && pnpm build && pnpm test  # contracts, bridge, tag unit tests
pnpm --filter tests-uns test       # UNS acceptance tests against the running stack
```

To watch the UNS, connect an MQTT client (e.g. MQTT Explorer) to `localhost:8883` with TLS and
the CA above, user `ignition` and `MQTT_IGNITION_PASSWORD` from `.env`, and subscribe to
`spBv1.0/#` and `delftssap/#`.

`docker compose -f docker-compose.yml up` runs without the dev port mappings, closer to the
Purdue zoning in [docs/prd/architecture.md](docs/prd/architecture.md).

## SCADA / HMI (Phase 4, in progress)

Ignition 8.3 Perspective, fed only from the UNS through Cirrus Link MQTT Engine (no PLC driver,
[ADR 0001](docs/adr/0001-uns-first.md)). Built so far:

- **Tags generated from the contract:** `pnpm gen:scada` writes one UDT per equipment type and
  the Line 1 instances (ISA-95 folders `Delft/Process|Packaging/Line1/…`) into
  [scada/tags/](scada/tags/) from the same metric catalog the edge bridge uses, so the HMI can
  never drift from the PLC map. Members reference the MQTT Engine tags (quality passes
  through); PLC alarms carry their priority, and an ack in Ignition acknowledges the alarm in
  the PLC.
- **Stop reasons:** [scada/reason-tree.json](scada/reason-tree.json), codes ≥ 100 by OEE loss
  category, shared by the HMI stop-reason popup and the MES.

Next: MQTT Engine connection, generated Perspective views (ISA-101 style), historian and alarm
journal on `scada-db`, and the gateway as a `docker compose` service (Ignition 8.3.10).
Development currently runs against a local Ignition gateway at `localhost:8088`, which reaches
the broker on `mqtts://localhost:8883`. Licensing uses the free
[Maker Edition](https://inductiveautomation.com/ignition/maker-edition) (non-commercial); its
key and activation token go in `.env` (`IGNITION_LICENSE_KEY`, `IGNITION_ACTIVATION_TOKEN`) and
are never committed.

## Repo map

| Folder | Layer | Status |
| --- | --- | --- |
| [sim/](sim/) | L0 simulator (Python) | done |
| [contracts/](contracts/) | Interfaces between layers | Modbus maps, UNS topics, JSON Schemas |
| [packages/contracts/](packages/contracts/) | TS types + metric catalog generated from contracts | done |
| [plc/](plc/) | L1 OpenPLC, Structured Text | done |
| [tests/fat/](tests/fat/) | PLC factory acceptance tests | done |
| [services/edge-bridge/](services/edge-bridge/) | Modbus ↔ MQTT / Sparkplug B (L1/L2 conduit) | done |
| [infra/broker/](infra/broker/) | EMQX UNS broker, TLS, ACL | done |
| [tests/uns/](tests/uns/) | UNS acceptance tests | done |
| [scada/](scada/) | Ignition Perspective HMI: generated tags, reason tree | Phase 4, in progress |
| `services/mes-api/`, `apps/mes-web/` | MES | Phase 5 |
| [docs/](docs/) | PRD, ADRs | |

## Next steps (a real plant)

- A second mix tank (T-102) so batching never limits the line (one tank has ~30% headroom).

## Honest scope

This project does not replace real commissioning experience: wiring, physical I/O, Profinet and
work at the machine. It shows the logic, integration and data side end to end.
