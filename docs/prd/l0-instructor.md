# L0 Instructor Station

Part of the [PRD](../prd.md). Folder: `apps/instructor/`. Stack: Next.js (`output: 'standalone'`), shared `packages/ui`.

## Purpose

A demo tool, not part of the plant. The presenter uses it to inject faults and watch the HMI and MES react. The idea comes from Operator Training Simulators (OTS): the instructor causes the upset, and the operator responds on the real HMI.

It is kept separate from the HMI and MES because a real operator has no "break the machine" button. Putting one in Ignition or MES would make the HMI unrealistic and would force MES onto the L0 network.

## Requirements

| ID | Requirement |
| --- | --- |
| INS-01 | Scenario buttons: capper jam, label roll empty, start drift on nozzle 7, steam pressure drop, sensor stuck, sensor disconnect |
| INS-02 | Time control: 1×, 10×, 60×, pause, reset with a seed input |
| INS-03 | **Run demo** plays `sim/scenarios/demo.yaml` so the recording is the same every time |
| INS-04 | Truth vs PLC view: true sensor value next to the value the PLC sees (noise, stuck, bad quality visible) |
| INS-05 | Event log: fault injected (time), and when the PLC reacted (from `/ws`) |
| INS-06 | Talks only to the sim API (REST + WS). No MQTT, no MES, no PLC access |
| INS-07 | Live pages are client components (`'use client'`). No SSR data fetching |
| INS-08 | Compact layout that fits a corner of the demo video (≈ 480 × 360) |

## Folder structure

```
apps/instructor/
├── Dockerfile
├── next.config.ts
└── src/
    ├── app/
    │   ├── layout.tsx
    │   └── page.tsx                  # single dashboard
    ├── components/
    │   ├── scenario-buttons.tsx
    │   ├── time-controls.tsx
    │   ├── truth-vs-plc-table.tsx
    │   └── event-log.tsx
    ├── hooks/
    │   └── use-sim-stream.ts         # WebSocket subscription
    └── api/
        └── sim-client.ts             # typed REST calls
```

## Acceptance criteria

- [ ] Each scenario button causes the expected alarm on the HMI within 5 s at 1×
- [ ] **Run demo** gives the same event timeline on two runs with the same seed
- [ ] A stuck sensor shows a frozen PLC value next to a moving true value
- [ ] The container is not attached to any L1 to L4 network
