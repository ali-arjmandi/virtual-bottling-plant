# L3 MES

Part of the [PRD](../prd.md). Folders: `services/mes-api/` (NestJS), `apps/mes-web/` (Next.js). DB: `mes-db` (PostgreSQL + TimescaleDB).

## Purpose

Manages production on Line 1 under ISA-95: work orders from ERP, recipe download, execution tracking, OEE, downtime, genealogy and quality. It is a UNS client only, with no path to the PLC or the simulator.

## Modules (build in this order)

| # | Module | Folder (`src/modules/`) |
| --- | --- | --- |
| 1 | UNS ingest | `uns/` |
| 2 | Work orders | `work-orders/` |
| 3 | Recipes | `recipes/` |
| 4 | Execution tracking | `execution/` |
| 5 | Downtime | `downtime/` |
| 6 | OEE | `oee/` |
| 7 | Genealogy | `genealogy/` |
| 8 | Quality | `quality/` |
| 9 | Shift reports + ERP sync | `shift-reports/`, `erp-integration/` |

## Requirements

### UNS ingest

| ID | Requirement |
| --- | --- |
| MES-01 | Subscribes to Sparkplug telemetry (decoder from `packages/contracts`) and JSON events |
| MES-02 | Stores raw signals it needs in Timescale hypertables (`signal_samples`, `machine_states`) |
| MES-03 | Idempotent on `messageId`; out-of-order messages are placed by `ts` |

### Work orders

| ID | Requirement |
| --- | --- |
| MES-10 | Receives orders from ERP ([contracts.md §5](contracts.md)). States: Received → Released → Running → Completed / Aborted |
| MES-11 | Only one work order Running on Line 1. Release starts the recipe download |
| MES-12 | Publishes work-order events to the UNS (retained) |

### Recipes

| ID | Requirement |
| --- | --- |
| MES-20 | Recipes are versioned. States: Draft → Approved → Obsolete. Only Approved versions can be downloaded |
| MES-21 | Approval needs a different user from the author (four-eyes) |
| MES-22 | Download via `cmd/recipe`; result stored with the work order. Nak blocks the start |

### Execution tracking

| ID | Requirement |
| --- | --- |
| MES-30 | Good and reject counts per work order, per lot and per shift, live from counters |
| MES-31 | Counter resets and rollovers are handled (deltas, not absolute values) |

### Downtime

| ID | Requirement |
| --- | --- |
| MES-40 | A downtime event opens when the constraint machine (F-401) leaves Execute during planned time |
| MES-41 | Root cause is the machine with the first-out alarm, so a filler "blocked" by the capper is booked on the capper |
| MES-42 | Reason from the HMI stop reason; uncoded stops are visible as "Unassigned" |
| MES-43 | Classified into the six big losses: breakdown (≥ 2 min, unplanned), setup/CIP, minor stop (< 2 min), reduced speed, startup reject, production reject |
| MES-44 | Pareto by reason, machine and loss category over any time range |

### OEE

| ID | Requirement |
| --- | --- |
| MES-50 | Availability = run time / planned production time (planned = shift time − planned breaks − no-order time) |
| MES-51 | Performance = (ideal cycle time × total count) / run time, ideal = 120 bpm at F-401 |
| MES-52 | Quality = good count / total count (good = passed Q-701 and not in a scrapped lot) |
| MES-53 | Per shift, per work order and live (rolling); dashboard refresh ≤ 5 s |
| MES-54 | Calculation is pure functions with unit tests on hand-worked examples |

### Genealogy

| ID | Requirement |
| --- | --- |
| MES-60 | Chain: concentrate lot → T-101 batch → P-201 run (temp curve) → product lot → pallet |
| MES-61 | Product lot = bottles from one batch within one work order. Code `L1-YYYYMMDD-NNN` |
| MES-62 | Batch changeover in T-301: bottles filled while two batches mix are linked to both (conservative) |
| MES-63 | Pallet = 100 cases (600 bottles) |
| MES-64 | Backward trace (lot → sources + P-201 temp curve) and forward trace (concentrate lot → all lots and pallets) |
| MES-65 | Trace query < 2 s on 30 days of data |
| MES-66 | P-201 temperatures for genealogy are stored in MES (critical control point record), not read from the SCADA historian |

### Quality

| ID | Requirement |
| --- | --- |
| MES-70 | X̄-R chart per nozzle from Q-701 subgroups (n = 5). Limits from the first 25 subgroups of an approved run |
| MES-71 | Rules: point outside 3σ, 7 points one side of centre (Western Electric 1 and 4) |
| MES-72 | Automatic lot hold on: SPC violation, batch Brix out of spec, divert during the lot's batch |
| MES-73 | Release or scrap by the QA role only, with a comment. Every change is audit-logged |
| MES-74 | Hold and release are published as lot events |

### Shift report and ERP sync

| ID | Requirement |
| --- | --- |
| MES-80 | At shift end: OEE, counts, top 5 stops, held lots. Viewable in web, sent to ERP |
| MES-81 | Work order completion sends a confirmation to ERP, retried until ERP acknowledges |

### Web UI (`apps/mes-web`)

| ID | Page |
| --- | --- |
| MES-90 | Dashboard: live OEE (A × P × Q), current work order, counts |
| MES-91 | Work orders: list, detail, release |
| MES-92 | Recipes: versions, diff, approve |
| MES-93 | Downtime: event list, Pareto |
| MES-94 | Quality: SPC per nozzle, held lots, release/scrap |
| MES-95 | Genealogy: search by lot, pallet or concentrate lot; tree + temp curve |
| MES-96 | Shift reports |

Roles (simple, seeded users): `operator`, `supervisor`, `qa`, `planner`.

## Folder structure

```
services/mes-api/
├── Dockerfile
└── src/
    ├── main.ts
    ├── app.module.ts
    ├── config/
    ├── db/
    │   ├── migrations/              # one migration per change
    │   └── seed/                    # products, reasons, users, recipes
    └── modules/
        └── work-orders/             # same shape for every module:
            ├── work-orders.module.ts
            ├── work-orders.controller.ts
            ├── work-orders.service.ts
            ├── work-orders.repository.ts
            ├── work-order-state.ts  # domain rules, no framework imports
            ├── dto/
            └── *.spec.ts

apps/mes-web/
└── src/
    ├── app/                         # one route folder per page (MES-90..96)
    ├── features/                    # oee/, downtime/, quality/, genealogy/, ...
    │   └── oee/                     # components + hooks for that feature only
    └── api/                         # typed client for mes-api
```

Inside a module, domain logic (state machines, OEE maths, SPC rules) lives in plain TS files with no NestJS imports, so it is easy to test and read.

## Data model (core tables)

`products`, `recipes`, `recipe_versions`, `work_orders`, `lots`, `pallets`, `batches`, `concentrate_lots`, `lot_links` (genealogy edges), `downtime_events`, `stop_reasons`, `machine_states` (hypertable), `signal_samples` (hypertable), `spc_subgroups` (hypertable), `quality_holds`, `shifts`, `audit_log`, `users`.

## Acceptance criteria

- [ ] Releasing WO-1042 downloads recipe v3 and the HMI shows Ack
- [ ] A capper jam appears as a downtime event on C-501 (not F-401), with the HMI reason
- [ ] Shift OEE matches a hand calculation from the raw events within 0.5 points
- [ ] Nozzle 7 drift triggers a hold on the open lot within 1 min of the violating subgroup
- [ ] Backward trace from a held lot shows the concentrate lot and the P-201 curve in < 30 s of user time
- [ ] Domain logic coverage ≥ 80%
