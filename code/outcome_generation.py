"""Latent outcome generation, kept separate from trial ordering."""

from __future__ import annotations

from itertools import groupby
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from trial_generation import CELLS


def _longest_run(values: Sequence[str]) -> int:
    return max((sum(1 for _ in group) for _, group in groupby(values)), default=0)


def assign_stratified_outcomes(
    schedule: Sequence[Mapping[str, Any]], rng: np.random.Generator
) -> List[Dict[str, Any]]:
    """Assign per-cell outcomes matching configured probability frequencies.

    Multiple independent shuffles are evaluated and the candidate with the
    shortest global same-outcome run is retained. This discourages long runs
    without imposing an artificial alternating sequence.
    """
    best: List[Dict[str, Any]] = []
    best_score = 10**9
    for _ in range(128):
        candidate = [dict(trial) for trial in schedule]
        for skew, info in CELLS:
            indices = [
                index
                for index, trial in enumerate(candidate)
                if trial["skew_condition"] == skew and trial["information_condition"] == info
            ]
            p_gain = float(candidate[indices[0]]["p_gain_actual"])
            gains = int(round(len(indices) * p_gain))
            outcomes = np.array(["gain"] * gains + ["loss"] * (len(indices) - gains), dtype=object)
            rng.shuffle(outcomes)
            for index, outcome in zip(indices, outcomes.tolist()):
                candidate[index]["outcome_preassigned"] = outcome
        sequence = [trial["outcome_preassigned"] for trial in candidate]
        longest = _longest_run(sequence)
        switches = sum(left != right for left, right in zip(sequence, sequence[1:]))
        alternating_penalty = max(0, switches - int(len(sequence) * 0.8))
        score = longest * 100 + alternating_penalty
        if score < best_score:
            best, best_score = candidate, score
        if longest <= 4 and alternating_penalty == 0:
            break
    return best


class ProbabilityGenerator:
    """Clean probability interface for future cue-distribution extensions."""

    def probability_for_trial(self, trial: Mapping[str, Any], rng: np.random.Generator) -> float:
        """Return the trial's stable cue probability in this implementation."""
        del rng
        return float(trial["p_gain_actual"])

