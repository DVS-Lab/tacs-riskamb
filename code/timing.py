"""Timing helpers and Monte Carlo duration estimates."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

import numpy as np


def jitter_ms(bounds: Tuple[int, int] | list[int], rng: np.random.Generator) -> int:
    """Sample an inclusive uniform integer duration."""
    return int(rng.integers(int(bounds[0]), int(bounds[1]) + 1))


def simulate_durations(
    config: Mapping[str, Any],
    rt_median_ms: float,
    rt_sigma: float = 0.30,
    simulations: int = 10000,
    seed: int = 20260620,
) -> Dict[str, float]:
    """Monte Carlo run duration under a truncated lognormal RT model."""
    rng = np.random.default_rng(seed)
    trials = int(config["task"]["trials"])
    timing = config["timing_ms"]
    rt = rng.lognormal(np.log(rt_median_ms), rt_sigma, size=(simulations, trials))
    rt = np.minimum(rt, float(timing["choice_deadline"]))
    fixation = rng.uniform(*timing["fixation"], size=(simulations, trials))
    delay = rng.uniform(*timing["pre_feedback"], size=(simulations, trials))
    iti = rng.uniform(*timing["iti"], size=(simulations, trials))
    fixed = float(timing["selection_highlight"] + timing["feedback"])
    total_ms = (rt + fixation + delay + iti + fixed).sum(axis=1)
    buffer_ms = float(timing["start_buffer"]) if config["task"].get("start_buffer_enabled") else 0.0
    total_ms += buffer_ms
    return {
        "median_minutes": float(np.median(total_ms) / 60000.0),
        "p90_minutes": float(np.percentile(total_ms, 90) / 60000.0),
        "start_buffer_seconds_included": buffer_ms / 1000.0,
    }

