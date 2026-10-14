"""Full truth snapshot for GET /state and the WebSocket stream: true and reported values."""

from __future__ import annotations

from typing import Any

from sim.runtime import SimRuntime


def snapshot(rt: SimRuntime) -> dict[str, Any]:
    p = rt.plant
    return {
        "tMs": rt.t_ms,
        "simTime": rt.clock.to_datetime(rt.t_ms).isoformat(),
        "speed": rt.clock.speed,
        "paused": rt.clock.paused,
        "seed": rt.seed,
        "machines": {
            name: {
                "status": m.status.status.value,
                "cause": list(m.status.cause),
                "runCmd": m.run_cmd,
                "speed": round(m.speed, 1),
                "count": m.cycles,
            }
            for name, m in p.machines.items()
        },
        "conveyors": {n: {"fill": c.fill, "capacity": c.capacity} for n, c in p.conveyors.items()},
        "process": {
            "T101": {"levelPct": round(p.mix_tank.tank.level_pct, 2),
                     "brix": round(p.mix_tank.tank.brix, 3),
                     "mixedness": round(p.mix_tank.mixedness, 3), "lotNo": p.mix_tank.lot_no},
            "P201": {"outletC": round(p.pasteurizer.outlet_c, 2),
                     "flowLpm": round(p.pasteurizer.flow_lpm, 1),
                     "divert": p.pasteurizer.divert_open,
                     "steamFactor": round(p.pasteurizer.steam_factor, 3)},
            "T301": {"levelPct": round(p.buffer.tank.level_pct, 2)},
            "cip": {"active": p.cip.active, "done": p.cip.done},
        },
        "sensors": {
            name: {
                "true": round(s.true_value, 3),
                "reported": round(s.reported, 3),
                "override": s.override.mode if s.override else None,
            }
            for name, s in p.sensors.sensors.items()
        },
        "faults": [
            {"id": f.id, "machine": f.machine, "type": f.spec.type, "kind": f.spec.kind,
             "startMs": f.start_ms, "endMs": f.end_ms, "source": f.source}
            for f in p.injector.active()
        ],
        "disconnectedUnits": sorted(rt.disconnected_units()),
    }
