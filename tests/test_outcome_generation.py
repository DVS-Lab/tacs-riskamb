from collections import Counter

import numpy as np

from config import load_config
from outcome_generation import assign_stratified_outcomes
from trial_generation import CELLS, generate_schedule


def test_default_stratified_outcomes_match_targets():
    schedule, _, _ = generate_schedule(load_config(), "001", "1", 1, 12)
    result = assign_stratified_outcomes(schedule, np.random.default_rng(12))
    for skew, info in CELLS:
        counts = Counter(
            t["outcome_preassigned"]
            for t in result
            if t["skew_condition"] == skew and t["information_condition"] == info
        )
        expected = {"gain": 10, "loss": 10} if skew == "symmetric" else {"gain": 5, "loss": 15}
        assert counts == expected


def test_outcomes_are_reproducible():
    schedule, _, _ = generate_schedule(load_config(), "001", "1", 1, 44)
    first = assign_stratified_outcomes(schedule, np.random.default_rng(44))
    second = assign_stratified_outcomes(schedule, np.random.default_rng(44))
    assert [t["outcome_preassigned"] for t in first] == [t["outcome_preassigned"] for t in second]

