# Interface Contracts

Part of the [PRD](../prd.md). Every interface between layers. The machine-readable versions live in `contracts/`; this file describes the rules. If the two disagree, `contracts/` wins and this file must be fixed.

## 1. Sim ↔ PLC (Modbus TCP, `contracts/modbus/sim-io.yaml`)

The sim is a Modbus TCP server; the PLC is the client (an OpenPLC Slave Device).

- **One unit ID per equipment.** Unit ID = the tag's hundreds digit: T-101 → 1, P-201 → 2, T-301 → 3, F-401 → 4, C-501 → 5, L-601 → 6, Q-701 → 7, K-801 → 8. Conveyors are unit 9.
- **Direction by register type:**

| Modbus type | Direction | Holds |
| --- | --- | --- |
| Discrete inputs | sim → PLC | Digital sensors (jam, roll empty, valve feedback) |
| Input registers | sim → PLC | Analog sensors, counters, sim clock |
| Coils | PLC → sim | Digital outputs (motor run, valve open) |
| Holding registers | PLC → sim | Analog outputs (speed setpoint, steam valve %) |

- **Scaling:** integers with a fixed scale in the YAML, e.g. temperature ×10 (`852` = 85.2 °C), Brix ×100, weight ×10 g.
- **32-bit values** (counters, sim time) use two registers, high word first.
- **Sim clock:** unit 9 IR 0–1 hold sim time in ms (mod 2³²). The PLC uses it as its time base (see [l1-plc.md](l1-plc.md)).
- **Quality data:** Q-701 reports per-nozzle subgroup stats (mean, range, n=5, sequence no.) instead of single bottles, like a real checkweigher.

Example rows (full list in YAML):

| Unit | Type | Addr | Name | Scale | Unit |
| --- | --- | --- | --- | --- | --- |
| 2 | IR | 0 | `TT201_InTemp` | ×10 | °C |
| 2 | IR | 1 | `TT202_OutTemp` | ×10 | °C |
| 2 | HR | 0 | `TCV201_SteamValve` | ×10 | % |
| 2 | Coil | 0 | `XV203_Divert` | bool | |
| 5 | DI | 0 | `C501_Jam` | bool | |

## 2. PLC ↔ edge bridge (Modbus TCP, `contracts/modbus/plc-io.yaml`)

The PLC's built-in Modbus server is read and written only by the edge bridge. Logic data uses OpenPLC memory words (`%MW`, holding 1024+) and double words (`%MD`, holding 2048+).

| Range | Direction | Content |
| --- | --- | --- |
| `%MW0`–`%MW799` | PLC → bridge | Per-equipment status, 50 words per block (state, mode, alarms, process values) |
| `%MW800`–`%MW899` | bridge → PLC | Commands (start, stop, reset, ack alarm, stop reason code) |
| `%MW900`–`%MW999` | both | Recipe block + handshake |
| `%MD0`–`%MD99` | PLC → bridge | 32-bit counters (good, reject, total per machine) |

### Recipe handshake

| Step | Who | Action |
| --- | --- | --- |
| 1 | Bridge | Writes recipe values, `RecipeId`, `RecipeVersion` |
| 2 | Bridge | Sets `Recipe_Req = 1` |
| 3 | PLC | Checks ranges and that the line is not in Execute. Sets `Recipe_Ack = 1` or `Recipe_Nak = <code>` |
| 4 | Bridge | Publishes the result to the UNS, clears `Recipe_Req` |
| 5 | PLC | Clears Ack/Nak when Req goes to 0 |

Timeout: 10 s without Ack/Nak counts as a failure.

### Command handshake

Commands are one-shot: the bridge writes the command word, and the PLC executes it and writes it back as 0. The stop reason is written to the PackML `Admin.StopReason` of that machine.

## 3. UNS (MQTT, `contracts/uns/topics.yaml`)

Two kinds of traffic on one broker:

| Kind | Format | Publisher | Consumers |
| --- | --- | --- | --- |
| Telemetry (tags) | Sparkplug B | Edge bridge | Ignition, MES |
| Events and commands | JSON (UTF-8), schema in `contracts/schemas/` | Edge bridge, MES, Ignition | MES, Ignition, edge bridge |

### Sparkplug B

- Group ID `DelftsSap`, edge node `Line1`, one device per equipment: `T101`, `P201`, `T301`, `F401`, `C501`, `L601`, `Q701`, `K801`, `CV`.
- Metric names follow the tag names in `plc-io.yaml` (`TT202_OutTemp`, `State`, `GoodCount`).
- Commands from Ignition come as `DCMD` (`Cmd_Start`, `Cmd_Stop`, `StopReason`, `AlarmAck`).
- When the PLC link is lost, the bridge publishes `DDEATH`, or marks metrics as stale. Ignition shows bad quality.

### JSON topic tree (ISA-95)

`delftssap/delft/{area}/line1/{cell}/{topic}`, where `area` is `process` or `packaging`.

| Topic | Publisher | Retained | Payload |
| --- | --- | --- | --- |
| `…/packaging/line1/{cell}/state` | bridge | yes | PackML state changes |
| `…/process/line1/mixer/batch` | bridge | no | Batch start/end, concentrate lot, Brix |
| `…/process/line1/pasteurizer/divert` | bridge | no | Divert start/end |
| `…/packaging/line1/events/workorder` | MES | yes | Work order released/started/completed |
| `…/packaging/line1/events/lot` | MES | no | Lot opened/closed/held/released |
| `…/packaging/line1/cmd/recipe` | MES | no | Recipe download request |
| `…/packaging/line1/cmd/recipe/result` | bridge | no | Ack/Nak + reason |

Every JSON message has: `ts` (ISO 8601 UTC, sim time), `source`, `schemaVersion` and a `messageId` (UUID) used for idempotency.

### ACL

| Client | Publish | Subscribe |
| --- | --- | --- |
| `edge-bridge` | `spBv1.0/DelftsSap/+/Line1/#`, state/batch/divert, `cmd/recipe/result` | `DCMD`, `cmd/recipe` |
| `ignition` | `DCMD` | everything read-only |
| `mes-api` | `events/#`, `cmd/recipe` | everything read-only |

## 4. Simulator API (REST + WebSocket, L0 only)

Base `http://sim:8000`. Used only by the Instructor Station and the FAT suite.

| Method | Path | Body / notes |
| --- | --- | --- |
| GET | `/state` | Full truth snapshot (true and reported sensor values) |
| POST | `/faults` | `{machine: "C501", type: "jam", durationS?: 30}` |
| DELETE | `/faults/{id}` | Clear an active fault |
| POST | `/sensors/{tag}/override` | `{mode: "stuck" \| "disconnect" \| "noise", value?}` |
| POST | `/clock` | `{speed: 1 \| 10 \| 60, paused?: bool}` |
| POST | `/reset` | `{seed: 42}` |
| POST | `/scenarios/{name}/run` | e.g. `demo` |
| WS | `/ws` | State stream at 2 Hz, plus fault and event log |

## 5. ERP ↔ MES (REST, ISA-95 B2MML-style JSON)

| Direction | Method | Path | Body |
| --- | --- | --- | --- |
| ERP → MES | POST | `mes-api/api/erp/work-orders` | `{orderNo, productCode, quantity, dueDate}` |
| MES → ERP | POST | `erp/api/confirmations` | `{orderNo, goodQty, scrapQty, start, end, lots[]}` |
| MES → ERP | POST | `erp/api/shift-reports` | Shift summary |

Both sides accept repeated calls with the same `orderNo`/`messageId` without creating duplicates.

## 6. Versioning

- Every schema has `schemaVersion`. A breaking change means a new major version and an ADR.
- `packages/contracts` is generated from `contracts/` (`pnpm gen:contracts`). CI fails if it is out of date.
- `sim` loads `sim-io.yaml` at startup. A FAT test checks that the PLC IO map matches it.
