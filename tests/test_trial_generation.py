from collections import Counter

from config import load_config
from trial_generation import (
    CELLS,
    cell_counts,
    counterbalance_cues,
    generate_schedule,
    schedule_constraints_hold,
)


def test_default_cell_counts_and_information_balance():
    config = load_config()
    schedule, _, _ = generate_schedule(config, "001", "1", 1, 123)
    assert cell_counts(schedule) == Counter({cell: 20 for cell in CELLS})
    assert sum(t["information_condition"] == "risk" for t in schedule) == 40
    assert sum(t["information_condition"] == "hidden_probability" for t in schedule) == 40


def test_no_negative_skew_and_balanced_sides_per_cell():
    schedule, _, _ = generate_schedule(load_config(), "001", "1", 1, 456)
    assert {t["skew_condition"] for t in schedule} == {"symmetric", "positive_skew"}
    for cell in CELLS:
        trials = [t for t in schedule if (t["skew_condition"], t["information_condition"]) == cell]
        assert Counter(t["gamble_side"] for t in trials) == {"left": 10, "right": 10}


def test_order_constraints_hold_across_1000_seeds():
    config = load_config()
    for seed in range(1000):
        schedule, _, _ = generate_schedule(config, "101", "2", 3, seed)
        assert schedule_constraints_hold(schedule), seed


def test_each_miniblock_has_two_trials_per_cell():
    schedule, _, _ = generate_schedule(load_config(), "001", "1", 1, 9)
    for block in range(1, 11):
        block_trials = [t for t in schedule if t["mini_block"] == block]
        assert Counter((t["skew_condition"], t["information_condition"]) for t in block_trials) == Counter({cell: 2 for cell in CELLS})


def test_cue_mapping_is_reproducible_rotates_and_reverses_on_reuse():
    cues = load_config()["cue_library"]
    first = counterbalance_cues("001", 1, cues)
    assert first == counterbalance_cues("001", 1, cues)
    assert {c["id"] for c in first.values()} != {c["id"] for c in counterbalance_cues("001", 2, cues).values()}
    reused = counterbalance_cues("001", 5, cues)
    assert first["symmetric"]["id"] == reused["positive_skew"]["id"]
    assert first["positive_skew"]["id"] == reused["symmetric"]["id"]


def test_test_mode_has_two_trials_per_cell():
    config = load_config("config/test.json")
    schedule, _, _ = generate_schedule(config, "T", "1", 1, 1)
    assert cell_counts(schedule) == Counter({cell: 2 for cell in CELLS})

