# L1 PLC (OpenPLC, Structured Text)

Part of the [PRD](../prd.md). Folder: `plc/`. Tools: OpenPLC Runtime v3 in Docker (pinned, headless, [ADR 0005](../adr/0005-openplc-portable-st.md)); ST authored as plain files, OpenPLC Editor optional. Status: **built in Phase 2**, see [plc/README.md](../../plc/README.md).

## Purpose

All control logic for Line 1: PackML state machines, interlocks, pasteuriser PID with divert, alarms and the recipe handshake. Written in portable IEC 61131-3 ST so it can move to CODESYS, TwinCAT or Siemens SCL with small changes.

## Requirements

### Structure

| ID | Requirement |
| --- | --- |
| PLC-01 | One generic `FB_PackML` (states: Stopped, Idle, Starting, Execute, Suspended, Held, Aborted, Complete, plus their transition states) used by every packaging machine |
| PLC-02 | One FB per machine type (`FB_Filler`, `FB_Capper`, `FB_Labeler`, `FB_Checkweigher`, `FB_CasePacker`) wrapping `FB_PackML` |
| PLC-03 | `FB_Tank` for T-101 and T-301, `FB_Pasteurizer` for P-201, `FB_MixBatch` for the ISA-88 phases of T-101 (fill, mix, transfer) |
| PLC-04 | IO mapping is the only code that touches `%IX/%QX/%IW/%QW`: one generated `IO_<EQ>` program per remote I/O station, from `sim-io.yaml`. Logic uses named variables in `G_In` / `G_Out`. Changing "hardware" means changing only the map. Likewise the generated `Bridge_*` programs are the only code with `%MW/%MD` |
| PLC-05 | Tag names follow ISA-5.1 (`TT202_OutTemp`, `LT301_Level`) |

### Behaviour

| ID | Requirement |
| --- | --- |
| PLC-10 | Suspended = starved (no input) or blocked (output full). Held = internal fault (jam, empty roll) |
| PLC-11 | Interlock: F-401 cannot run unless `LT301_Level` ≥ 20% (restarts at 25%, hysteresis). P-201 cannot forward-flow below 83 °C |
| PLC-12 | PID on `TT202_OutTemp` → steam valve, SP 85 °C, with flow feedforward from `FT201_Flow` (without it, every transfer start diverts for minutes; see Phase 1 findings in [l0-simulator.md](l0-simulator.md)) and gain scheduled on flow. Divert valve opens below 83 °C and closes after 30 s stable at SP − 0.5 °C or above (a noisy reading never stays strictly above SP). SP can be changed from the bridge (`P201_TempSP`, 70–90 °C) for tests |
| PLC-13 | PackML `Admin.StopReason` is set by the HMI command, or automatically for known causes |
| PLC-14 | Timers and the PID dt use the sim clock register, not wall-clock time, so logic holds under time acceleration (risk R1) |
| PLC-15 | Loss of communication to a sim unit raises a comms alarm and puts that machine in Held. Detected by a per-unit heartbeat register (sim-io v1.1) frozen for 1.5 s real time, because OpenPLC keeps the last values on a timeout |
| PLC-16 | Line start/stop from the local panel (sim operator) or the HMI line command: start runs from K-801 back to F-401 (`FB_LineSequencer`). Starved = input empty **and** upstream machine not in Execute |
| PLC-17 | One mix tank only (Phase 1 finding: ~30% spare capacity is enough). A second tank T-102 is a "next step" in the README |

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
├── src/
│   ├── types/                # ST_Recipe.st, ST_MachineCmd.st
│   ├── time/                 # FB_SimClock.st, FB_SimTon.st (sim-clock time base)
│   ├── packml/               # FB_PackML.st, FB_PackagingUnit.st, PackMLHasStarted.st
│   ├── machines/             # FB_Filler.st, FB_Capper.st, ..., FB_LineSequencer.st
│   ├── process/              # FB_Tank.st, FB_PID.st, FB_Pasteurizer.st, FB_MixBatch.st
│   ├── alarms/               # FB_Alarm.st, FB_CommsWatchdog.st
│   ├── recipe/               # FB_RecipeHandshake.st
│   ├── generated/            # from contracts/modbus/*.yaml: types, gvl, io/IO_<EQ>,
│   │                         # bridge/Bridge_*, alarms/FB_AlarmTable (never edited by hand)
│   └── PRG_Main.st
├── scripts/
│   ├── gen_plc_io.py         # contracts → src/generated + runtime/mbconfig.cfg (--check in CI)
│   ├── build.sh              # concatenates src/ into build/line1.st (OpenPLC takes one file)
│   └── check_file_sizes.sh
└── runtime/                  # Dockerfile, start.sh, configure.sql, generated mbconfig.cfg
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
| `test_io_map_matches_contract` | Every `sim-io.yaml` signal is mapped in `IO_*` at the address OpenPLC gives it (recomputed independently of the generator); no located variables outside the generated maps |
| `test_pid_step_response` | 75 → 85 °C step: settles to 85 ± 0.5 °C within 3 min, overshoot < 1 °C |
| `test_first_out_alarm` | C-501 jam then L-601 label error → only the jam is first-out; ack per alarm id |
| `test_recipe_accepted_when_stopped` | Valid download while stopped → Ack; setpoints follow the recipe |
| `test_line_stop_and_start_command` | HMI line stop → all Stopped; start → all Execute |

## Acceptance criteria

- [ ] All FAT tests pass in CI against Dockerised sim + runtime
- [ ] PID settles to 85 ± 0.5 °C within 3 min after a 10 °C step, with < 1 °C overshoot
- [ ] No FB file over 300 lines; `PRG_Main` only calls FBs
- [ ] README section explains structure, naming and how it would port to CODESYS
