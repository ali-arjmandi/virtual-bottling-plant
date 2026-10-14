# Edge Bridge and Unified Namespace

Part of the [PRD](../prd.md). Folders: `services/edge-bridge/` (TypeScript, modbus-serial, Sparkplug B client) and `infra/broker/` (EMQX).

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
| UNS-01 | EMQX with TLS on 8883. Plain 1883 disabled outside dev |
| UNS-02 | One user per client with ACL from [contracts.md §3](contracts.md) |
| UNS-03 | Topic tree and metric names come from `contracts/uns/topics.yaml` |

## Folder structure

```
services/edge-bridge/
├── Dockerfile
└── src/
    ├── main.ts                  # wiring only
    ├── config/env.ts            # validated env
    ├── modbus/
    │   ├── plc-client.ts        # connection + reconnect
    │   ├── block-reader.ts      # polls blocks, decodes with the map
    │   └── write-queue.ts
    ├── sparkplug/
    │   ├── node-session.ts      # BIRTH/DEATH, seq numbers
    │   └── metric-publisher.ts  # report by exception
    ├── events/
    │   ├── state-change-detector.ts
    │   └── event-publisher.ts
    ├── commands/
    │   ├── dcmd-handler.ts
    │   └── recipe-handshake.ts
    └── health/health-server.ts  # /health for compose
```

## Acceptance criteria

- [ ] Ignition sees all Line 1 devices through its MQTT Engine without manual tag creation
- [ ] Stopping the PLC container shows bad quality in Ignition within 1 s of the 3rd missed poll
- [ ] A recipe download round trip (MES → PLC → result) takes < 2 s
- [ ] Unit tests cover decoding (scaling, 32-bit words), deadband and the handshake state machine
- [ ] Broker refuses a `mes-api` attempt to publish `DCMD`
