# ADR 0002: Modbus TCP between simulator and PLC (remote-I/O model)

Status: accepted (Phase 1) · Date: 2026-10-14

## Context

The simulator stands in for the machines. The PLC must see it the way it would see real field
devices, so the control logic can later move to real hardware with only the I/O mapping changed.

## Decision

- The simulator is a **Modbus TCP server**, one unit ID per equipment (T-101 → 1 … K-801 → 8,
  line/conveyors → 9). The PLC (OpenPLC Slave Device) is the client, like a remote I/O station.
- Register map in `contracts/modbus/sim-io.yaml` is the single source of truth: the sim loads it
  at start-up, and a FAT test will check the PLC IO map against it.
- The simulator exposes **causes only** (jam bit, empty roll, conveyor full). PackML state,
  interlocks and every decision live in the PLC.
- A unit whose sensor is "disconnected" does not reply, so the PLC sees a timeout, as with a
  dead remote I/O station.
- We wrote a small Modbus server (`sim/io/modbus_pdu.py`, `modbus_server.py`, ~150 lines)
  instead of using pymodbus' server: its datastore API is mid-migration in 3.x, and we need exact
  control over "no reply". pymodbus is kept as the test client.

## Consequences

- Modbus has no authentication: the sim and PLC share `net-l0-field` (internal network) only,
  which is the IEC 62443 zone/conduit story in the README.
- Values are scaled integers (×10, ×100) and 32-bit counters span two registers, high word first.
- Per-bottle data does not fit Modbus polling; the checkweigher reports per-nozzle subgroups.
