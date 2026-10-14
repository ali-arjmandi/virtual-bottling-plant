# L4 ERP Stub

Part of the [PRD](../prd.md). Folder: `services/erp/` (NestJS, in-memory or SQLite store).

## Purpose

A minimal stand-in for the business system. It sends work orders down to MES and receives confirmations and shift reports, so the ISA-95 L4 ↔ L3 flow is visible end to end. It is not an ERP.

## Requirements

| ID | Requirement |
| --- | --- |
| ERP-01 | Seed list of orders (e.g. WO-1042: orange juice 1 L, 12,000 bottles) |
| ERP-02 | `POST /api/orders/{orderNo}/send` pushes the order to MES ([contracts.md §5](contracts.md)) |
| ERP-03 | Receives confirmations and shift reports; stores and lists them |
| ERP-04 | Idempotent on `orderNo` / `messageId` |
| ERP-05 | Minimal page or Swagger UI to send orders and view confirmations |
| ERP-06 | Only on `net-l4-business`; reaches MES only through its API |

## Folder structure

```
services/erp/
├── Dockerfile
└── src/
    ├── main.ts
    ├── orders/            # orders.controller.ts, orders.service.ts, seed-orders.ts
    ├── confirmations/     # confirmations.controller.ts, confirmations.service.ts
    └── mes-client/        # mes-client.ts
```

## Acceptance criteria

- [ ] Sending WO-1042 creates it in MES as Received
- [ ] Completing it in MES shows a confirmation in ERP with good and scrap quantities and lot codes
- [ ] Sending the same order twice creates one order in MES
