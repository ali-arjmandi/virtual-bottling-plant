# AI Shift Assistant (optional, Phase 6)

Part of the [PRD](../prd.md). Folder: `ai/`. Built only after the four core layers are complete.

## Purpose

Answers supervisor questions about production in plain language, for example "Why did Line 1 stop last night?" or "Which nozzle had the most rejects this week?". It connects to MES data through an MCP server.

## Requirements

| ID | Requirement |
| --- | --- |
| AI-01 | MCP server exposes read-only tools over the MES API (not the DB directly): `get_oee`, `get_downtime`, `get_pareto`, `trace_lot`, `get_spc`, `get_shift_report` |
| AI-02 | Read-only. No tool can release orders, change recipes or release lots |
| AI-03 | Answers cite the data they used (time range, lot codes, event IDs) |
| AI-04 | Runs in L3 (`net-l3-operations`) and uses a scoped MES API token |
| AI-05 | Uses the latest Claude model via the Anthropic SDK; model ID in env |

## Folder structure

```
ai/
├── Dockerfile
└── src/
    ├── server.ts           # MCP server setup
    ├── tools/              # one file per tool
    └── mes-client.ts
```

## Acceptance criteria

- [ ] "Why did Line 1 stop last night?" returns the top stop reasons with times and machines, matching the MES Pareto
- [ ] Any write intent gets a refusal that says the assistant is read-only
