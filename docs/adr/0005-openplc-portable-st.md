# ADR 0005: OpenPLC Runtime v3 with portable Structured Text

Status: accepted (Phase 2) · Date: 2026-10-14

## Context

L1 must run in Docker on an Apple Silicon Mac and in CI, with no Windows tools (NFR-01), and
the control code should read like a real PLC project that could move to CODESYS, TwinCAT or
Siemens SCL.

## Decision

- **Runtime:** OpenPLC Runtime v3, built from source at a pinned commit
  (`b5d4135`, 2026-04) in `plc/runtime/Dockerfile`. It builds and runs natively on arm64.
- **Headless:** no web UI steps. At image build, `configure.sql` sets RUN mode and disables
  DNP3/EtherNet-IP/S7, `build.sh` concatenates `plc/src/` into `line1.st`, and
  `compile_program.sh` compiles it. Slave devices come from `mbconfig.cfg`, generated from
  `contracts/modbus/sim-io.yaml` by `plc/scripts/gen_io_config.py`.
- **Code:** IEC 61131-3 ST in many small files (one POU per file), concatenated for OpenPLC's
  one-file limit (risk R4). Function blocks take data only through their inputs and outputs;
  only the three programs (`IO_Map`, `Bridge_Map`, `PRG_Main`) touch globals.
- **Comms loss:** each sim unit exposes a free-running `{EQ}_Heartbeat` register (sim-io v1.1).
  `FB_CommsWatchdog` raises a comms alarm when it does not change for 1.5 s of real time.

## Spike findings (2026-10-14)

| Question | Finding | Consequence |
| --- | --- | --- |
| arm64 Docker | Builds from source in ~3 min, runs natively | No emulation needed |
| Slave address layout | Devices are polled in file order; each type is packed from `%IX100.0`, `%QX100.0`, `%IW100`, `%QW100` | Addresses generated into `plc/runtime/io_addresses.csv`, never hand-computed |
| Slave host | libmodbus `modbus_new_tcp` takes an IP, not a hostname | `start.sh` resolves `sim` at start-up and fills the `@SIM_HOST@` placeholder |
| Enum with values (`(STOPPED := 2)`) | Rejected by matiec | PackML state numbers are `INT` constants in `GVL_Constants` |
| Located vars next to FB/struct instances in one `VAR` block | Rejected by matiec | Located vars go in their own `VAR` block |
| `SHL` / `OR` on `UDINT` | Rejected (bit-string types only) | 32-bit join: `hi * 65536 + lo` |
| Globals in a POU | Need `VAR_EXTERNAL` (strict IEC) | Only programs use globals |
| `%MD` word order on the Modbus server | High word first | Matches contracts.md |
| Unit not replying | Last values are **kept** (no quality flag); the poll cycle grows from ~120 ms to ~400 ms with a 250 ms timeout | Heartbeat watchdog needed (PLC-15); keep the slave timeout low |
| Web UI | Saving slave devices or settings regenerates `mbconfig.cfg` from the empty DB table | Web UI is for monitoring only; documented in `configure.sql` |

## Porting to CODESYS / TwinCAT

Only these change: `IO_Map` (fieldbus mapping instead of `%IW100…`), `Bridge_Map` (OPC UA or
ADS symbols instead of `%MW`), and the `CONFIGURATION` block. Enums can then carry explicit
values, and `VAR_EXTERNAL` declarations can stay (both accept them).

## Consequences

- The PLC image is slow to build from scratch (C++ deps); CI caches the layer.
- OpenPLC has no per-slave status for the program; the heartbeat makes comms health explicit,
  as a real remote I/O station's diagnostic word would.
