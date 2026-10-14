# ADR 0003: PackML state model for every packaging machine

Status: accepted (Phase 2) · Date: 2026-10-14

## Context

F-401 to K-801 are five different machines, but the HMI, the MES downtime logic and any later
line integrator need to read them the same way: is it producing, waiting, faulted or stopped,
and why.

## Decision

- Every packaging machine runs the same `FB_PackML` (ISA-TR88.00.02 states, numbered as in the
  standard). Machine FBs (`FB_Filler`, …) wrap it through `FB_PackagingUnit` and only add their
  own causes and setpoints.
- **Held** = an internal cause at this machine (jam, breakdown, material out, comms lost).
  **Suspended** = an external cause: *blocked* (output conveyor full) or *starved* (input empty
  **and** the upstream machine not in Execute). The upstream condition matters: downstream
  machines run faster than the filler, so their input is empty between bottles all the time.
- In Suspended the motor stays on and the machine resumes by itself, as a real monoblock does.
  The exception is the filler interlock (T-301 below 20 %), which also drops the run output.
- Acting states (Starting, Holding, Stopping…) complete on the motor feedback or after 5 s, so
  a missing feedback cannot lock a machine in a transition.
- `Admin.StopReason`: the alarm id (1–99) when the machine holds; the operator's reason code
  (≥ 100) from the HMI overrides it; cleared when the machine re-enters Execute.
- First-out alarm: the first alarm raised while the table was clear is flagged, so MES books a
  filler that is *blocked* by a capper jam on the capper (MES-41).
- Line start (panel or HMI) starts machines from the case packer back to the filler; line state
  = F-401 state (the constraint).

## Consequences

- One state model for the HMI faceplate (`UDT_PackMLMachine`) and for MES downtime rules.
- matiec enums cannot carry values, so the PackML numbers live in `plc-io.yaml` and the
  generated `PackMLStateToInt` converts at the bridge boundary (ADR 0005).
- Complete/Completing exist for completeness but no machine uses them yet (no batch-count end).
