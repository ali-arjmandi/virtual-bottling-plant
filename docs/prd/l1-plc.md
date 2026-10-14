# L1 PLC (OpenPLC, Structured Text)

Part of the [PRD](../prd.md). Folder: `plc/`. Tools: OpenPLC Editor v4 (macOS), OpenPLC Runtime in Docker.

## Purpose

All control logic for Line 1: PackML state machines, interlocks, pasteuriser PID with divert, alarms and the recipe handshake. Written in portable IEC 61131-3 ST so it can move to CODESYS, TwinCAT or Siemens SCL with small changes.

## Requirements

### Structure

| ID | Requirement |
| --- | --- |
| PLC-01 | One generic `FB_PackML` (states: Stopped, Idle, Starting, Execute, Suspended, Held, Aborted, Complete, plus their transition states) used by every packaging machine |
| PLC-02 | One FB per machine type (`FB_Filler`, `FB_Capper`, `FB_Labeler`, `FB_Checkweigher`, `FB_CasePacker`) wrapping `FB_PackML` |
| PLC-03 | `FB_Tank` for T-101 and T-301, `FB_Pasteurizer` for P-201, `FB_MixBatch` for the ISA-88 phases of T-101 (fill, mix, transfer) |
| PLC-04 | IO mapping (`IO_Map`) is the only code that touches `%IX/%QX/%IW/%QW`. Logic uses named variables in `GVL_IO`. Changing "hardware" means changing only the map |
| PLC-05 | Tag names follow ISA-5.1 (`TT202_OutTemp`, `LT301_Level`) |

### Behaviour

| ID | Requirement |
| --- | --- |
| PLC-10 | Suspended = starved (no input) or blocked (output full). Held = internal fault (jam, empty roll) |
| PLC-11 | Interlock: F-401 cannot start unless `LT301_Level` > 20%. P-201 cannot forward-flow below 83 °C |
| PLC-12 | PID on `TT202_OutTemp` → steam valve, SP 85 °C, with flow feedforward from `FT201_Flow` (without it, every transfer start diverts for minutes; see Phase 1 findings in [l0-simulator.md](l0-simulator.md)). Divert valve opens below 83 °C and closes after 30 s stable above 85 °C |
| PLC-13 | PackML `Admin.StopReason` is set by the HMI command, or automatically for known causes |
| PLC-14 | Timers and the PID dt use the sim clock register, not wall-clock time, so logic holds under time acceleration (risk R1) |
| PLC-15 | Loss of communication to a sim unit raises a comms alarm and puts that machine in Held |

### Alarms

| ID | Requirement |
| --- | --- |
| PLC-20 | `FB_Alarm` per alarm: priority (1–4), active, acknowledged, first-out flag |
| PLC-21 | Alarm table published in the status block; ack command from the bridge |
| PLC-22 | First-out: the first alarm in a cascade is flagged, so the HMI and MES can tell cause from symptom |

### Recipe

| ID | Requirement |
| --- | --- |
| PLC-30 | `ST_Recipe`: product code, Brix target ± tol, concentrate ratio, fill target weight, line speed, cap torque |
| PLC-31 | `FB_RecipeHandshake` implements the Req/Ack/Nak handshake from [contracts.md §2](contracts.md). It rejects out-of-range values and downloads while in Execute |

## Folder structure

```
plc/
├── openplc/                  # OpenPLC Editor project files
├── src/
│   ├── types/                # ST_Recipe.st, E_PackMLState.st, ST_Alarm.st
│   ├── gvl/                  # GVL_IO.st, GVL_Status.st, GVL_Commands.st
│   ├── io/                   # IO_Map.st
│   ├── packml/               # FB_PackML.st
│   ├── machines/             # FB_Filler.st, FB_Capper.st, ...
│   ├── process/              # FB_Tank.st, FB_PID.st, FB_Pasteurizer.st, FB_MixBatch.st
│   ├── alarms/               # FB_Alarm.st, FB_AlarmManager.st
│   ├── recipe/               # FB_RecipeHandshake.st
│   └── PRG_Main.st
├── scripts/build.sh          # concatenates src/ into build/line1.st (OpenPLC takes one file)
└── runtime/                  # Dockerfile, slave-device config for the sim units
```

## Tests (FAT)

Folder: `tests/fat/` (pytest). Each test sets up a scenario through the sim API and checks PLC outputs over Modbus.

| Test | Expectation |
| --- | --- |
| `test_buffer_empty_blocks_filler` | T-301 level < 20% → F-401 Suspended; does not restart until above threshold |
| `test_low_temp_diverts` | Outlet temp < 83 °C → divert opens within 1 scan; closes after 30 s stable |
| `test_capper_jam_cascade` | C-501 jam → C-501 Held, F-401 Suspended (blocked) after the conveyor fills |
| `test_recipe_rejected_in_execute` | Download while running → Nak |
| `test_recipe_out_of_range` | Brix target 20 → Nak with a range code |
| `test_comms_loss` | Sim unit disconnect → comms alarm + Held |
| `test_io_map_matches_contract` | Every `sim-io.yaml` signal is mapped in `IO_Map` |

## Acceptance criteria

- [ ] All FAT tests pass in CI against Dockerised sim + runtime
- [ ] PID settles to 85 ± 0.5 °C within 3 min after a 10 °C step, with < 1 °C overshoot
- [ ] No FB file over 300 lines; `PRG_Main` only calls FBs
- [ ] README section explains structure, naming and how it would port to CODESYS
