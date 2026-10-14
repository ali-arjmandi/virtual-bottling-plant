# Architecture, Layer Boundaries and Repo Structure

Part of the [PRD](../prd.md). Defines how layers are separated and how the repo is organised.

## 1. Zones and conduits (Purdue / IEC 62443)

Each zone is one Docker network. A service joins only the networks listed here.

| Zone (network) | Purdue | Services |
| --- | --- | --- |
| `net-l0-field` | L0 | `sim`, `plc` |
| `net-l0-instructor` | L0 tool | `sim` (API only), `instructor` |
| `net-l1-control` | L1 | `plc`, `edge-bridge` |
| `net-l2-supervisory` | L2 | `edge-bridge`, `broker`, `ignition`, `scada-db` |
| `net-l3-operations` | L3 | `broker`, `mes-api`, `mes-web`, `mes-db` |
| `net-l4-business` | L4 | `mes-api`, `erp` |

Conduits (the only allowed cross-zone paths):

| From | To | Protocol | Notes |
| --- | --- | --- | --- |
| `plc` | `sim` | Modbus TCP | PLC is the Modbus client, sim is remote I/O |
| `edge-bridge` | `plc` | Modbus TCP | The only client of the PLC |
| `edge-bridge`, `ignition`, `mes-api` | `broker` | MQTT over TLS | Per-client ACL |
| `erp` | `mes-api` | HTTPS REST | Work orders down, confirmations up |
| `instructor` | `sim` | REST + WebSocket | Demo tool, never on L1 to L4 |

Rules:

- MES never reaches the PLC or the simulator.
- Ignition has no Modbus driver to the PLC (UNS-first, a deliberate trade-off).
- The Ignition historian DB (`scada-db`) and the MES DB (`mes-db`) are separate instances.
- Only `mes-web`, `ignition` and `instructor` publish ports to the host, plus the broker dashboard in dev.

## 2. Dependency rules for code

1. A layer folder never imports from another layer folder.
2. Shared things live in `contracts/` (language-neutral) and `packages/` (TS only).
3. Data flows only through the conduits above, never through a shared DB or file.
4. Each service reads its config from env vars, validated at startup.

## 3. Repo structure

```
virtual-bottling-plant/
├── README.md
├── docker-compose.yml
├── .env.example
├── pnpm-workspace.yaml
├── docs/
│   ├── prd.md
│   ├── prd/                      # one PRD per layer + cross-cutting docs
│   └── adr/                      # one decision per file: 0001-uns-first.md
├── contracts/                    # source of truth for every interface
│   ├── modbus/sim-io.yaml        # sim ↔ PLC register map
│   ├── modbus/plc-io.yaml        # PLC ↔ edge bridge register map
│   ├── uns/topics.yaml           # topic tree + Sparkplug metric names
│   └── schemas/                  # JSON Schema, one file per message/API body
├── sim/                          # L0, Python
├── plc/                          # L1, IEC 61131-3 ST
├── services/
│   ├── edge-bridge/              # L1/L2 conduit, TypeScript
│   ├── mes-api/                  # L3, NestJS
│   └── erp/                      # L4, NestJS
├── apps/
│   ├── mes-web/                  # L3, Next.js
│   └── instructor/               # L0 tool, Next.js
├── packages/
│   ├── ui/                       # shared React components and styles
│   └── contracts/                # TS types + decoders generated from /contracts
├── scada/                        # L2, Ignition project + tag exports
├── ai/                           # optional MCP server
├── tests/fat/                    # cross-layer PLC acceptance tests (pytest)
├── infra/
│   ├── broker/                   # EMQX config, ACL
│   ├── db/                       # init scripts, one folder per DB
│   └── certs/                    # generated locally, gitignored
└── .github/workflows/
```

The internal layout of each folder is in its layer PRD.

## 4. Code conventions

### Size and shape

- One responsibility per file. Target ≤ 200 lines, hard limit 300. Split before you pass it.
- One exported class, function block or React component per file.
- No `utils`, `helpers`, `common` or `misc` files. Name the file after what it does (`brix-calculator.ts`, not `utils.ts`).
- Folders are grouped by domain (`work-orders/`), not by type (`controllers/`).

### Naming

| Language | Files | Symbols |
| --- | --- | --- |
| TypeScript | `kebab-case.ts`, `work-order.service.ts` | `PascalCase` classes, `camelCase` functions |
| Python | `snake_case.py` | PEP 8 |
| Structured Text | `FB_Filler.st`, `PRG_Main.st`, `GVL_IO.st` | `FB_`, `PRG_`, `GVL_`, `ST_` (struct), `E_` (enum) prefixes |
| Tags / signals | ISA-5.1 style | `TT201_OutTemp`, `LT301_Level`, `WT701_Weight` |
| Docker services | `kebab-case` | `mes-api`, `edge-bridge` |

Equipment IDs keep the plan's tags: `T-101` in docs and UI, `T101` in code, topics and Sparkplug.

### Tests

- TypeScript: `*.spec.ts` next to the file under test.
- Python: `sim/tests/` mirrors `sim/src/sim/`.
- Cross-layer acceptance: `tests/fat/`.

## 5. Architecture decisions to record (ADRs)

One short file each in `docs/adr/`:

1. UNS-first instead of SCADA drivers to the PLC
2. Modbus TCP between simulator and PLC (remote-I/O model)
3. PackML state model for every packaging machine
4. ISA-101 high-performance HMI style
5. OpenPLC with portable ST (and how it would move to CODESYS or TwinCAT)
6. Telemetry over Sparkplug B, events over JSON
7. Separate historian and MES databases
