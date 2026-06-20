#!/usr/bin/env python3
"""Estimate full-run duration for several plausible RT distributions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from config import DEFAULT_CONFIG, load_config  # noqa: E402
from timing import simulate_durations  # noqa: E402


PROFILES = {
    "fast_younger_adult": {"rt_median_ms": 550.0, "rt_sigma": 0.28},
    "typical_younger_adult": {"rt_median_ms": 800.0, "rt_sigma": 0.30},
    "slower_responder": {"rt_median_ms": 1100.0, "rt_sigma": 0.35},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--simulations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260620)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    results = {
        name: simulate_durations(config, simulations=args.simulations, seed=args.seed + index, **profile)
        for index, (name, profile) in enumerate(PROFILES.items())
    }
    payload = {
        "trials": config["task"]["trials"],
        "choice_deadline_ms": config["timing_ms"]["choice_deadline"],
        "buffer_included": bool(config["task"].get("start_buffer_enabled")),
        "profiles": results,
    }
    print(json.dumps(payload, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

