"""Objective information-state snapshots available before each choice."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Mapping, Optional


LEARNING_COLUMNS = [
    "prior_cue_exposures",
    "prior_visible_probability_cue_exposures",
    "prior_hidden_probability_cue_exposures",
    "prior_observed_gains",
    "prior_observed_losses",
    "prior_empirical_gain_rate",
    "trials_since_cue_first_shown",
    "exact_probability_previously_displayed",
    "most_recently_displayed_probability",
    "most_recent_realized_outcome_for_cue",
]


class LearningTracker:
    """Track cue-specific information without leaking the current outcome."""

    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "exposures": 0,
                "visible": 0,
                "hidden": 0,
                "gains": 0,
                "losses": 0,
                "first_trial": None,
                "exact_seen": False,
                "last_probability": None,
                "last_outcome": None,
            }
        )

    def before(self, trial: Mapping[str, Any]) -> Dict[str, Any]:
        """Return state strictly prior to the supplied trial."""
        state = self._state[str(trial["cue_id"])]
        observed = state["gains"] + state["losses"]
        first: Optional[int] = state["first_trial"]
        return {
            "prior_cue_exposures": state["exposures"],
            "prior_visible_probability_cue_exposures": state["visible"],
            "prior_hidden_probability_cue_exposures": state["hidden"],
            "prior_observed_gains": state["gains"],
            "prior_observed_losses": state["losses"],
            "prior_empirical_gain_rate": state["gains"] / observed if observed else None,
            "trials_since_cue_first_shown": int(trial["trial_number"]) - first if first is not None else None,
            "exact_probability_previously_displayed": state["exact_seen"],
            "most_recently_displayed_probability": state["last_probability"],
            "most_recent_realized_outcome_for_cue": state["last_outcome"],
        }

    def observe(self, trial: Mapping[str, Any], outcome_shown: bool = True) -> None:
        """Update state after feedback for a completed trial."""
        state = self._state[str(trial["cue_id"])]
        if state["first_trial"] is None:
            state["first_trial"] = int(trial["trial_number"])
        state["exposures"] += 1
        if trial["information_condition"] == "risk":
            state["visible"] += 1
            state["exact_seen"] = True
            state["last_probability"] = float(trial["p_gain_actual"])
        else:
            state["hidden"] += 1
        if outcome_shown:
            outcome = str(trial["outcome_preassigned"])
            state["gains" if outcome == "gain" else "losses"] += 1
            state["last_outcome"] = outcome
