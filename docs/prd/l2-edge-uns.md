# Edge Bridge and Unified Namespace

Part of the [PRD](../prd.md). Folders: `services/edge-bridge/` (TypeScript, modbus-serial, mqtt, sparkplug-payload) and `infra/broker/` (EMQX 5.8). Decisions: [ADR 0001 UNS-first](../adr/0001-uns-first.md), [ADR 0006 Sparkplug + JSON](../adr/0006-sparkplug-telemetry-json-events.md). Status: **built in Phase 3**.

## Purpose

The bridge is the only conduit between the control zone (L1) and everything above. It reads the PLC over Modbus TCP, publishes telemetry with Sparkplug B and events as JSON, and writes commands and recipes back to the PLC.

## Requirements

### Read path (PLC → UNS)

| ID | Requirement |
| --- | --- |
| EDG-01 | Polls the PLC status and counter blocks every 250 ms (configurable). Map loaded from `contracts/modbus/plc-io.yaml` |
| EDG-02 | Publishes `NBIRTH`/`DBIRTH` on start and `DDATA` with report-by-exception (deadband per metric from the map) |
| EDG-03 | Detects PackML state changes and publishes JSON state events (retained) |
| EDG-04 | Publishes batch and divert events from PLC status edges |
| EDG-05 | Poll timeouts mark affected metrics stale and, after 3 misses, publish `DDEATH` for that device. Recovery re-births |
| EDG-06 | Timestamps use the PLC sim clock, so history lines up under acceleration |

### Write path (UNS → PLC)

| ID | Requirement |
| --- | --- |
| EDG-10 | Handles `DCMD` from Ignition: start, stop, reset, alarm ack, stop reason |
| EDG-11 | Handles `cmd/recipe` from MES: validates against the JSON Schema, runs the handshake, publishes `cmd/recipe/result` |
| EDG-12 | Writes are serialised (one write queue) so commands and recipe never interleave |
| EDG-13 | Rejects commands for unknown devices or metrics and logs them |

### Broker

| ID | Requirement |
| --- | --- |
| UNS-01 | EMQX with TLS on 8883. Plain 1883 disabled outside dev. A one-shot `certs` service makes a local dev CA (`infra/certs/gen-certs.sh`) |
| UNS-02 | One user per client (passwords from `.env`) with ACL from [contracts.md §3](contracts.md), generated into `infra/broker/acl.conf` |
| UNS-03 | Topic tree and metric names come from `contracts/uns/topics.yaml` |

## Folder structure

```
packages/contracts/              # generated from /contracts: pnpm gen:contracts
├── scripts/gen.ts, gen-acl.ts   # TS types, contract constants, infra/broker/acl.conf
└── src/
    ├── metric-catalog.ts        # every Sparkplug metric and the PLC word behind it
    ├── uns-topics.ts, validators.ts
    └── generated/               # never edited by hand

services/edge-bridge/
├── Dockerfile                   # build context: repo root
└── src/
    ├── main.ts                  # wiring only
    ├── config/env.ts            # validated env
    ├── bridge/line-bridge.ts    # one poll cycle: read, publish, events, handshake
    ├── modbus/
    │   ├── plc-client.ts        # connection, reconnect, timeouts
    │   ├── write-queue.ts       # one queue for every Modbus transaction
    │   ├── read-plan.ts         # which %MW spans / %MD counters a poll reads
    │   ├── block-reader.ts      # polls the blocks into a raw snapshot
    │   └── value-decoder.ts     # signed, scaled, enum, alarm bits, 32-bit
    ├── sparkplug/
    │   ├── node-session.ts      # BIRTH/DEATH, bdSeq, seq, NCMD/DCMD
    │   ├── metric-publisher.ts  # report by exception
    │   └── quality-tracker.ts   # stale / dead / bad quality
    ├── time/sim-timestamp.ts    # sim clock → epoch ms (EDG-06)
    ├── events/                  # state-change-detector, process-event-detector, event-publisher
    ├── commands/                # dcmd-handler, recipe-handshake, recipe-words
    └── health/health-server.ts  # /health for compose

infra/broker/                    # emqx.conf, start.sh (users from env), acl.conf (generated)
tests/uns/                       # acceptance tests against the running stack (Vitest)
```

## Acceptance criteria

- [ ] Ignition sees all Line 1 devices through its MQTT Engine without manual tag creation (Phase 4; births with every contract metric are checked in `tests/uns/specs/sparkplug.spec.ts`)
- [x] Stopping the PLC container gives `DDEATH` for every device within 1 s of the 3rd missed poll (`link-loss.spec.ts`)
- [x] A recipe download round trip (MES → PLC → result) takes < 2 s (~0.1–0.3 s measured)
- [x] Unit tests cover decoding (scaling, 32-bit words), deadband and the handshake state machine
- [x] Broker refuses a `mes-api` attempt to publish `DCMD` (`acl.spec.ts`)
