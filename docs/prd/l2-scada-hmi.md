# L2 SCADA / HMI (Ignition Perspective)

Part of the [PRD](../prd.md). Folder: `scada/`. Tool: Ignition Maker Edition in Docker (Perspective, MQTT Engine, MQTT Transmission).

## Purpose

The operator's view of Line 1: high-performance HMI screens, alarms, historian and stop-reason entry. Ignition gets all PLC data from the UNS (Sparkplug B), not from a PLC driver.

## Requirements

### Tag model

| ID | Requirement |
| --- | --- |
| SCA-01 | One UDT per equipment type: `UDT_PackMLMachine` (base), `UDT_Filler`, `UDT_Capper`, `UDT_Labeler`, `UDT_Checkweigher`, `UDT_CasePacker`, `UDT_Tank`, `UDT_Pasteurizer` |
| SCA-02 | Instances bound to MQTT Engine tags by parameter (device name), so a new line is new instances only |
| SCA-03 | Tag folders follow the ISA-95 path: `Delft/Process/Line1/…`, `Delft/Packaging/Line1/…` |
| SCA-04 | Bad and stale quality shown on every bound value (no silent last value) |

### Screens (ISA-101)

| ID | Screen | Content |
| --- | --- | --- |
| SCA-10 | Plant overview | Line status, rate, active alarm count, current work order (from UNS event) |
| SCA-11 | Line view | All 8 units + conveyor fill, PackML state, counts, blocked/starved shown clearly |
| SCA-12 | Machine faceplate | Popup per machine: state, mode, key values, alarms, start/stop/reset |
| SCA-13 | Batch / process | T-101 phase, Brix, P-201 temp trend, divert status, T-301 level |
| SCA-14 | Alarms | Active table + journal, ack, filter by priority and area |

| ID | Style rule |
| --- | --- |
| SCA-20 | Grey background, muted equipment. Colour only for abnormal states and alarm priority |
| SCA-21 | Analog values shown with their normal range (moving-analog indicators, not plain numbers) |
| SCA-22 | Style classes in one place (`scada/projects/delfts-hmi/styles/`), no inline colours |

### Operator actions

| ID | Requirement |
| --- | --- |
| SCA-30 | Stop-reason popup when a machine has been stopped > 2 min without a reason. Reason list from a shared reason tree |
| SCA-31 | Stop reason, start, stop, reset and ack go out as `DCMD` |
| SCA-32 | The recipe handshake result is shown on the line view (recipe ID, version, Ack/Nak) |

### History

| ID | Requirement |
| --- | --- |
| SCA-40 | Tag historian on `scada-db` (PostgreSQL): temps, levels, speeds, counts |
| SCA-41 | Trends for P-201 temps and tank levels on the batch screen |
| SCA-42 | Alarm journal stored in `scada-db` |

## Folder structure

```
scada/
├── projects/delfts-hmi/        # Perspective project (file-based resources, mounted)
│   ├── views/                  # overview/, line/, faceplates/, batch/, alarms/, popups/
│   ├── styles/
│   └── scripts/                # small project library scripts only
├── tags/
│   ├── udts/                   # one JSON export per UDT
│   └── instances/line1.json
├── gateway/README.md           # manual gateway setup steps (MQTT Engine, DB, alarm journal)
└── reason-tree.json            # stop reasons, shared with MES seed data
```

## Acceptance criteria

- [ ] A C-501 jam shows: C-501 Held with an alarm, F-401 later Suspended (blocked), downstream Suspended (starved), all readable in one glance
- [ ] Stop-reason popup appears after 2 min and the reason reaches MES
- [ ] Disconnecting a sensor in the Instructor Station shows bad quality on that value only
- [ ] Screens use no colour on a healthy running line
- [ ] Adding a second filler instance needs no new view or script
