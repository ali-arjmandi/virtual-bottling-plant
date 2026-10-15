# ADR 0006: Telemetry over Sparkplug B, events and commands over JSON

Status: accepted (Phase 3) · Date: 2026-10-14

## Context

Two kinds of data cross the UNS. Tag values (temperatures, states, counters) change every
poll and need typed values, quality and a way to tell a dead source from a quiet one. Events
and commands (a batch started, a lot held, a recipe download) are rare, need idempotency and
a schema, and must be readable by tools that do not speak Sparkplug.

## Decision

- **Telemetry: Sparkplug B** (`spBv1.0/DelftsSap/…/Line1/{device}`). Births carry every
  metric with its type; data is report-by-exception with a deadband per metric from
  `plc-io.yaml`; `NDEATH` (MQTT will, `bdSeq`) and `DDEATH` mark a lost source. Ignition's MQTT
  Engine builds its tags from the births. Each metric has a `Quality` property (192 good, 0
  bad, 500 stale) so a lost remote I/O station shows bad quality on its values only.
- **Events and commands: JSON** on the ISA-95 tree (`delftssap/delft/{area}/line1/…`), one
  JSON Schema per message in `contracts/schemas/`, with an envelope of `ts`, `source`,
  `schemaVersion` and `messageId`. The publisher validates before sending; the bridge
  validates recipe commands before they reach the PLC.
- **Sim time everywhere.** Sparkplug and event timestamps are `SIM_EPOCH` + the PLC's sim
  clock, not wall time, so history and OEE line up when the simulation runs at ×10 (EDG-06).
- **Commands from the HMI are Sparkplug `DCMD`** on writable metrics (`Cmd_Start`,
  `StopReason`, `AlarmAck`), because that is what an Ignition tag write produces. Recipe
  downloads from the MES are JSON, because they are a request with a result.

## Consequences

- Two decoders for consumers (protobuf and JSON); `packages/contracts` gives the TS ones.
- Sparkplug's per-message `seq` and `bdSeq` let a consumer detect gaps and restarts.
- Retained JSON state topics give a late subscriber the current PackML state at once;
  Sparkplug state comes from a rebirth request instead.
- Sim-time timestamps run ahead of wall time at ×10; trends must use the sim clock for "now"
  (Phase 4 risk).
