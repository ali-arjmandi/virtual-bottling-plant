# L1 Soft-PLC (OpenPLC, IEC 61131-3 Structured Text)

All control decisions for Line 1: PackML state machines, interlocks, the pasteuriser PID with
divert, the ISA-88 batch sequence, alarms with first-out, and the recipe handshake. The
simulator only makes physics and failures; nothing moves unless this program says so.
Requirements: [docs/prd/l1-plc.md](../docs/prd/l1-plc.md) · Decisions:
[ADR 0003 PackML](../docs/adr/0003-packml-state-model.md),
[ADR 0005 OpenPLC](../docs/adr/0005-openplc-portable-st.md).

## Run

```bash
docker compose up --build            # sim + plc; PLC Modbus on 127.0.0.1:5502, web UI on :8080
pip install -r tests/fat/requirements.txt
python -m pytest tests/fat -v        # FAT suite against the running containers (~10 min at ×10)
```

The web UI (login `openplc` / `openplc`) is for watching only. Program, slave devices and
settings are baked into the image; saving settings in the UI would overwrite them.

## Structure

```
plc/src/
├── PRG_Main.st          wiring only: calls every FB once per scan
├── types/               ST_Recipe, ST_MachineCmd
├── time/                FB_SimClock (time base from the sim clock), FB_SimTon
├── packml/              FB_PackML, FB_PackagingUnit, PackMLHasStarted
├── machines/            FB_Filler, FB_Capper, FB_Labeler, FB_Checkweigher, FB_CasePacker,
│                        FB_LineSequencer, FB_LineStatus
├── process/             FB_MixBatch (T-101), FB_Pasteurizer + FB_PID (P-201), FB_Tank (T-301)
├── alarms/              FB_Alarm, FB_CommsWatchdog
├── recipe/              FB_RecipeHandshake
└── generated/           from contracts/modbus/*.yaml, never edited by hand:
    ├── types/           enums (+ XToInt / IntToX), process-image and status structs
    ├── gvl/             global variables
    ├── io/              IO_<EQ>: one program per remote I/O station (%IX/%QX/%IW/%QW)
    ├── bridge/          Bridge_*: status, alarms, counters, commands, recipe (%MW/%MD)
    └── alarms/          FB_AlarmTable: one FB_Alarm instance per alarm
```

| Layer | Touches | Who writes it |
| --- | --- | --- |
| `IO_*` programs | sim registers ↔ `G_In` / `G_Out` (engineering units) | generator |
| `Bridge_*` programs | `G_Status`, `G_Alarms`… ↔ `%MW` / `%MD` | generator |
| Function blocks | only their inputs and outputs | hand-written |
| `PRG_Main` | globals ↔ FB inputs/outputs | hand-written |

One scan (50 ms task): `IO_*` and `Bridge_*` copy the process images first, then `PRG_Main`
runs the logic. Outputs reach the field one scan later, well under the ~120 ms Modbus poll.

### Why generated maps

OpenPLC has no located arrays, so each of ~270 registers needs its own declaration. A
register list belongs in the contract, not in hand-typed ST: `plc/scripts/gen_plc_io.py`
writes the maps from `contracts/modbus/sim-io.yaml` and `plc-io.yaml`, CI fails if they are
stale, and `tests/fat/test_io_map_matches_contract.py` recomputes every address independently.

```bash
python3 plc/scripts/gen_plc_io.py         # after editing a contract (needs PyYAML)
plc/scripts/build.sh                      # concatenates src/ into build/line1.st (R4)
plc/scripts/check_file_sizes.sh           # no file over 300 lines
```

## Naming

| Kind | Convention | Example |
| --- | --- | --- |
| Function block / function | `FB_` / verb-ish name | `FB_Pasteurizer`, `PackMLHasStarted` |
| Program | `PRG_`, generated `IO_`, `Bridge_` | `PRG_Main`, `IO_P201` |
| Struct / enum | `ST_` / `E_` | `ST_Recipe`, `E_PackMLState` |
| Globals | `G_` | `G_In.TT202_OutTemp` |
| Tags | ISA-5.1, equipment prefix | `TT202_OutTemp`, `LT301_Level`, `XV203_Divert` |
| Enum literals | prefix per enum | `PML_EXECUTE`, `PHASE_MIX`, `NAK_IN_EXECUTE` |

## Key behaviour

- **Time base:** timers and the PID run on the sim clock register (`FB_SimClock`, PLC-14), so
  the logic holds at ×10. Only the comms watchdog uses real time (a paused sim is not a fault).
- **Interlocks:** F-401 fills only while T-301 is above 20 % (restart at 25 %). P-201 diverts
  at once below 83 °C and returns to forward flow after 30 s stable within 0.5 °C of SP.
- **PID:** PI on TT202 with flow feedforward and gain scheduled on flow (the process gain is
  8× higher on recirculation). Pump starts/stops feed forward the commanded flow, since FT201
  arrives a poll cycle late.
- **Batch:** fill by flow totals → 15 min mix → Brix check (alarm, `BrixOk` for MES) →
  transfer. A recipe with another product drains T-101 and T-301 and runs CIP first. A tank
  found not empty in Idle (e.g. after a PLC restart) is mixed, checked and transferred.
- **Comms loss:** each remote I/O station has a heartbeat register. Frozen for 1.5 s → comms
  alarm and that machine Held. (OpenPLC keeps last values on a timeout, so values alone
  cannot tell.)

## Porting to CODESYS / TwinCAT

The function blocks and `PRG_Main` are plain IEC 61131-3 and move as they are. Replace the
generated `IO_*` with the fieldbus I/O mapping, the `Bridge_*` with OPC UA / ADS symbols, and
the `CONFIGURATION` block from `build.sh` with the target's task configuration. Enums can then
carry explicit values, which removes the `XToInt` conversion functions.
