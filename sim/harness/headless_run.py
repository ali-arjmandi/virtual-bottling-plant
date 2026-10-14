"""Harness only: run the sim as fast as possible with the stub controller and write
events.jsonl + summary.json.

    python -m harness.headless_run --hours 24 --seed 42 --out out/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness.run_summary import summarize
from harness.stub_controller import attach
from sim.config_models import load_config
from sim.io.register_map import RegisterMap
from sim.runtime import SimRuntime

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def run(hours: float, seed: int, out: Path, config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    events_path = out / "events.jsonl"
    end_ms = int(hours * 3600 * 1000)
    with events_path.open("w") as sink:
        runtime = SimRuntime(load_config(config_dir), RegisterMap.load(), seed, sink)
        attach(runtime)
        runtime.run_until(end_ms)
    plant = runtime.plant
    counts = {name: m.cycles for name, m in plant.machines.items()}
    counts["Q701_rejects"] = plant.checkweigher.reject_count
    counts["K801_cases"] = plant.case_packer.case_count
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    summary = summarize(events, plant.calendar.planned_windows(end_ms), end_ms, counts)
    summary.update({"seed": seed, "hours": hours})
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args()
    summary = run(args.hours, args.seed, args.out)
    print(json.dumps({k: v for k, v in summary.items() if k != "pareto"}, indent=2))
    for row in summary["pareto"]:
        print(f"  {row['minutes']:8.1f} min  {row['share']:6.1%}  {row['reason']}")


if __name__ == "__main__":
    main()
