# PRD: Virtual Bottling Plant (Delfts Sap B.V., Line 1)

| | |
| --- | --- |
| Owner | Ali |
| Status | Draft v1 |
| Date | 2026-10-14 |
| Source | [plan.md](../plan.md) |
| Repo | `virtual-bottling-plant` |

This file is the product-level PRD. Each layer has its own short PRD in [prd/](prd/). Read this file first, then only the layer you are building.

## 1. Problem

Delfts Sap B.V. (fictional juice producer) runs one 1 L PET bottling line on two shifts.

- Stops are logged on paper. Nobody knows the real OEE.
- Tracing a complaint bottle back to its concentrate batch takes a day.
- Recipes are typed by hand on the HMI. Typos create scrap.
- Fill-weight problems are found late, after bad product has shipped.

## 2. Goals

The product digitises Line 1 from PLC to MES on top of a physics-based simulator. It must show four outcomes in a live demo:

| ID | Outcome | Measure |
| --- | --- | --- |
| G1 | Live OEE per shift and per work order, with a reason for every stop | OEE updates within 5 s of a state change |
| G2 | Trace a bottle lot to its concentrate batch and pasteurisation curve | < 30 s for a user, < 2 s query |
| G3 | Recipe sent from MES to PLC, no manual typing | Handshake confirmed on HMI |
| G4 | Fill-weight quality alarm and automatic lot hold | Lot held within 1 min of an SPC violation |

Secondary goal: the repo is a hiring portfolio. Each layer must be readable on its own by a PLC, HMI, SCADA, MES or IT/OT reviewer.

## 3. Non-goals

- Real hardware, wiring, physical I/O, Profinet, on-site commissioning
- More than one line or site
- A real ERP, MRP, CMMS or WMS
- Production-grade auth and user management (basic roles only)
- Windows-only tools (CODESYS, TIA Portal, Ignition Vision)

## 4. Users

| Persona | Uses | Needs |
| --- | --- | --- |
| Operator | Ignition HMI | See line state, start/stop, enter stop reasons, acknowledge alarms |
| Shift supervisor | MES web | OEE, downtime Pareto, end-of-shift report |
| QA | MES web | SPC charts, lot hold/release, genealogy |
| Planner | ERP stub, MES web | Release work orders, see confirmations |
| Instructor (demo presenter) | Instructor Station | Inject faults, control time, run the scripted demo |
| Reviewer (recruiter, interviewer) | README, video | Understand the system in 30 s |

## 5. Scope by layer

Each layer is a separate deployable with one owner folder and one PRD.

| Purdue level | Component | Folder | PRD |
| --- | --- | --- | --- |
| L0 | Line simulator (Python) | `sim/` | [l0-simulator.md](prd/l0-simulator.md) |
| L0 (tool) | Instructor Station (Next.js) | `apps/instructor/` | [l0-instructor.md](prd/l0-instructor.md) |
| L1 | Soft-PLC (OpenPLC, ST) | `plc/` | [l1-plc.md](prd/l1-plc.md) |
| L1/L2 conduit | Edge bridge + MQTT broker (UNS) | `services/edge-bridge/`, `infra/broker/` | [l2-edge-uns.md](prd/l2-edge-uns.md) |
| L2 | SCADA / HMI (Ignition) | `scada/` | [l2-scada-hmi.md](prd/l2-scada-hmi.md) |
| L3 | MES API + web | `services/mes-api/`, `apps/mes-web/` | [l3-mes.md](prd/l3-mes.md) |
| L4 | ERP stub | `services/erp/` | [l4-erp.md](prd/l4-erp.md) |
| Optional | AI shift assistant (MCP) | `ai/` | [ai-assistant.md](prd/ai-assistant.md) |

Cross-cutting:

- [architecture.md](prd/architecture.md): zones, networks, dependency rules, repo structure, code conventions
- [contracts.md](prd/contracts.md): every interface between layers (Modbus maps, UNS topics, APIs)
- [demo-and-deliverables.md](prd/demo-and-deliverables.md): 5-minute demo script, README, video, CV text

## 6. Core principles

1. **The simulator makes physics and failures. The PLC makes decisions.** No control logic in `sim/`.
2. **Only the edge bridge talks to the PLC.** SCADA and MES are UNS clients only.
3. **Layers talk only through contracts** in `contracts/`. No layer imports another layer's code.
4. **Deterministic by seed.** The same seed gives the same faults at the same sim time.
5. **One command:** `docker compose up` starts everything on an Apple Silicon Mac.

## 7. Line model (summary)

Nominal rate 120 bottles/min (7,200/h). Full parameters are in [l0-simulator.md](prd/l0-simulator.md).

```
T-101 Mix ─► P-201 HTST ─► T-301 Buffer ─► F-401 Filler ─► C-501 Capper ─► L-601 Labeler ─► Q-701 Checkweigher ─► K-801 Case packer
  (batch, ISA-88)                          └──────────── accumulation conveyors (~150 bottles) between each ────────────┘
```

Operations: two shifts (06:00 to 14:00, 14:00 to 22:00), two flavours (orange, apple), and a 45-minute CIP on each product change.

## 8. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | Runs fully in Docker Desktop on macOS (arm64). No Windows dependency |
| NFR-02 | Cold start of the full stack in < 3 min after images are built |
| NFR-03 | Each Purdue zone is its own Docker network ([architecture.md](prd/architecture.md)) |
| NFR-04 | MQTT uses TLS and per-client ACLs |
| NFR-05 | Same seed gives the same run, checked in CI |
| NFR-06 | CI runs lint, unit tests and the PLC FAT suite on every push |
| NFR-07 | No secrets in git. `.env.example` lists every variable |
| NFR-08 | Source files stay small: target ≤ 200 lines, hard limit 300 |

## 9. Success criteria (release)

- [ ] A 24 h simulated run gives line OEE between 55% and 70%
- [ ] The downtime Pareto has one clear top reason
- [ ] The 5-minute demo runs end to end from **Run demo**, the same way twice in a row
- [ ] G1 to G4 are each shown in the demo
- [ ] The PLC FAT suite passes in CI
- [ ] The README has the story, a GIF, the architecture diagram, the role table and the one-command start

## 10. Phases

About 10 weeks at 15 to 20 h/week. Each phase ends with something you can demo.

| Phase | Weeks | Delivers | Exit criteria |
| --- | --- | --- | --- |
| P1 Simulator | 1–2 | `sim/`, Modbus server, fault API | 24 h headless run, line behaviour plausible (**done**) |
| P2 PLC | 3–4 | `plc/`, PackML, PID, alarms, FAT suite | FAT green; line runs under PLC control |
| P3 UNS | 5 | Edge bridge, broker, contracts | Sparkplug data visible in an MQTT client |
| P4 SCADA/HMI | 6 | Ignition UDTs, 5 screens, historian | **Apply for PLC/HMI/SCADA roles** |
| P5 MES + ERP | 7–9 | Work orders, recipe, OEE, downtime, genealogy, quality | Full demo runs; **apply for MES roles** |
| P6 Polish | 10 | Instructor Station demo mode, README, video, optional AI | Release criteria in §9 met |

## 11. Risks and open questions

| ID | Risk / question | Plan |
| --- | --- | --- |
| R1 | Time acceleration (×60) breaks PLC timers and PID, which run in real time | PLC timers use the sim clock register (see [l1-plc.md](prd/l1-plc.md)). Live chain is validated up to ×10. P1 result: the sim alone runs 24 h in ~50 s headless, so the history question is now about the PLC and MES, not the sim. Decide in P5 between ×60 live with coarser control or a seed generator that writes synthetic history (flagged as such) |
| R2 | Modbus polling cannot keep up with per-bottle data at high speed | The checkweigher reports per-nozzle subgroup stats, not single bottles ([contracts.md](prd/contracts.md)) |
| R3 | Ignition Maker Edition limits (non-commercial, no Vision) | Use Perspective only. Document the licence in the README |
| R4 | OpenPLC Runtime accepts one `.st` file | Keep modular sources, concatenate in `plc/scripts/build.sh` |
| R5 | Scope creep in MES | MES modules in priority order; AI is the last phase and optional |
| Q1 | EMQX or HiveMQ CE? | Default EMQX (built-in ACL and dashboard). Revisit in P3 |
