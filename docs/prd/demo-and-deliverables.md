# Demo and Deliverables

Part of the [PRD](../prd.md). What a reviewer sees. Everything here is built for a 30-second skim.

## 5-minute demo script

A story, not a feature tour. The same script is used for the video and for in-person interviews.

| Time | Step | Shows |
| --- | --- | --- |
| 0:00 | Problem slide: paper stops, unknown OEE, one-day trace | Context |
| 0:30 | Architecture diagram, one sentence per layer | Purdue / UNS |
| 1:00 | Release WO-1042 (orange, 12,000 bottles) in MES. Recipe v3 goes to the PLC; Ack on the HMI | G3 |
| 1:45 | HMI line view: counts and live OEE | G1 |
| 2:15 | Instructor Station (or **Run demo**): capper jam. Alarm; filler runs until the conveyor fills, then blocked. Operator enters the stop reason | PLC + HMI |
| 3:00 | MES: availability drops; 30-day downtime Pareto | G1 |
| 3:30 | Nozzle 7 drift: SPC alarm, lot held automatically | G4 |
| 4:00 | Trace the held lot to the concentrate batch and P-201 curve | G2 |
| 4:30 | Optional: one question to the AI assistant | AI |
| 4:50 | Close: "In a real plant, my next step would be…" | |

Before recording: fix the seed and play `demo.yaml` with **Run demo**.

Screen layout: Ignition HMI as the main image, MES dashboard beside it, Instructor Station small in a corner.

## Deliverables

| Deliverable | Content | Done when |
| --- | --- | --- |
| README | One-paragraph story, 10 s HMI GIF, architecture diagram, role table, `docker compose up`, honest scope note | Reviewer understands it in 30 s |
| Video (3–5 min) | Demo script above; YouTube unlisted or Loom; link at the top of README and in the CV | Recorded from **Run demo** |
| Case study (1-page PDF) | Problem → solution → result, one HMI and one OEE screenshot | |
| LinkedIn series | 4 posts: simulator, PLC, HMI/SCADA, MES; one image + one lesson each | |
| Interview notes | One "why" sentence per ADR (Modbus, PackML, ISA-101, UNS, OpenPLC) | |

## Role table (for README)

| Role | Proven by | Interview question it answers |
| --- | --- | --- |
| PLC / Controls | PackML FBs, interlocks, PID, alarms, FAT suite | How do you structure a PLC program so another engineer can maintain it? |
| HMI | ISA-101 Perspective screens, faceplates, stop-reason entry | What makes an operator screen good during an upset? |
| SCADA | UDTs, historian, alarm journal, Sparkplug ingest, quality handling | How do you design a tag structure that scales to 20 lines? |
| MES | Work orders, recipes, OEE, downtime, genealogy, SPC, ERP sync | How does a work order flow from ERP to the machine and back? |
| IIoT / IT-OT | Edge bridge, UNS on ISA-95, Purdue zones, IEC 62443 conduits | Why a Unified Namespace instead of point-to-point integrations? |

## Honest scope note (for README)

This project does not replace real commissioning experience: wiring, physical I/O, Profinet and work at the machine. It shows the logic, integration and data side end to end.

## CV entry

> **Virtual Bottling Plant** (personal project) · github.com/ali-arjmandi/virtual-bottling-plant
> Built an end-to-end PLC-to-MES system for a simulated juice bottling line: a physics-based line simulator with realistic failures and quality drift (Python), IEC 61131-3 control logic with PackML state machines and PID control (OpenPLC), an ISA-101 HMI/SCADA with alarms and historian (Ignition), a Modbus-to-MQTT Unified Namespace with Sparkplug B, and a TypeScript MES for work orders, recipe download, OEE and lot genealogy.

Replace the GitHub URL with the real one.
