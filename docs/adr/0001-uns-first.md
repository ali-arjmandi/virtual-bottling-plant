# ADR 0001: UNS-first instead of SCADA drivers to the PLC

Status: accepted (Phase 3) · Date: 2026-10-14

## Context

Ignition, the MES and later tools all need Line 1 data, and Ignition and the MES both send
things back (commands, stop reasons, recipes). The usual set-up gives each consumer its own
driver to the PLC: Ignition's Modbus driver, an MES OPC connection, and so on. Each one is
another Modbus client, another copy of the register map and another path into the control zone.

## Decision

- One **edge bridge** is the only client of the PLC. It publishes everything to an MQTT broker
  (the Unified Namespace) and is the only thing that writes to the PLC.
- Ignition and the MES are **UNS clients only**: Ignition has no Modbus driver to the PLC, and
  the MES has no network path to L1 at all (architecture.md §1).
- The broker is **EMQX** (open-source 5.8 line): TLS listener, built-in user database, file
  ACL, dashboard. HiveMQ CE has no built-in ACL without an extension, so it lost on UNS-02.
- The topic tree, the metric names and the ACL are all generated from
  `contracts/uns/topics.yaml` and `plc-io.yaml`, so a consumer never needs the register map.

## Consequences

- The PLC has one Modbus client: no concurrent writers, one write queue (EDG-12), and one
  place where register addresses live outside the PLC.
- IEC 62443 story: L1 (`net-l1-control`) and L2 (`net-l2-supervisory`) meet only in the
  bridge container. The broker sits on L2 and L3; the ACL decides who may command what.
- A new consumer (a second MES, a data lake, the AI assistant) subscribes; nothing changes at L1.
- The bridge is a single point of failure for data. A dead bridge or PLC shows as Sparkplug
  `DDEATH`, so consumers see bad quality instead of frozen values.
- Ignition gives up its driver's tag browser; MQTT Engine creates the tags from the births
  instead.
