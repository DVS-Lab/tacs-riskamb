from learning import LearningTracker


def _trial(number, outcome="gain", info="risk"):
    return {
        "trial_number": number,
        "cue_id": "cue_A",
        "information_condition": info,
        "p_gain_actual": 0.5,
        "outcome_preassigned": outcome,
    }


def test_pretrial_state_never_contains_current_outcome():
    tracker = LearningTracker()
    first = _trial(1, "gain")
    before_first = tracker.before(first)
    assert before_first["prior_observed_gains"] == 0
    assert before_first["prior_observed_losses"] == 0
    tracker.observe(first)
    second = _trial(2, "loss", "hidden_probability")
    before_second = tracker.before(second)
    assert before_second["prior_observed_gains"] == 1
    assert before_second["prior_observed_losses"] == 0
    assert before_second["exact_probability_previously_displayed"] is True
    tracker.observe(second)
    assert tracker.before(_trial(3))["prior_observed_losses"] == 1


def test_unshown_counterfactual_does_not_enter_observed_counts():
    tracker = LearningTracker()
    tracker.observe(_trial(1, "gain"), outcome_shown=False)
    state = tracker.before(_trial(2))
    assert state["prior_cue_exposures"] == 1
    assert state["prior_observed_gains"] == 0

