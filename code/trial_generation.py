"""Reproducible cue counterbalancing and constrained schedule generation."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np


SKEW_CONDITIONS = ("symmetric", "positive_skew")
INFORMATION_CONDITIONS = ("risk", "hidden_probability")
CELLS = tuple((skew, info) for skew in SKEW_CONDITIONS for info in INFORMATION_CONDITIONS)


def derive_seed(subject: str, session: str, run: int) -> int:
    """Derive a stable NumPy-compatible seed from BIDS identifiers."""
    digest = hashlib.sha256(f"{subject}|{session}|{int(run)}|riskambiguity".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


def _stable_parity(value: str) -> int:
    return hashlib.sha256(value.encode()).digest()[0] % 2


def counterbalance_cues(
    subject: str, run: int, cue_library: Sequence[Mapping[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Choose a run-specific pair and reproducibly map cues to gamble types.

    Pairs rotate across successive runs. When a pair is reused, its mapping is
    reversed, providing a new learning episode without depending on Python's
    process-randomized ``hash``.
    """
    pairs = [cue_library[index : index + 2] for index in range(0, len(cue_library), 2)]
    cycle = (int(run) - 1) // len(pairs)
    pair = pairs[(int(run) - 1) % len(pairs)]
    flip = (_stable_parity(str(subject)) + cycle) % 2
    ordered = pair[::-1] if flip else pair
    return {
        "symmetric": dict(ordered[0]),
        "positive_skew": dict(ordered[1]),
    }


def _max_run_ok(previous: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any], field: str) -> bool:
    values = [trial[field] for trial in previous[-3:]] + [candidate[field]]
    return not (len(values) == 4 and len(set(values)) == 1)


def schedule_constraints_hold(schedule: Sequence[Mapping[str, Any]]) -> bool:
    """Return whether all cross-trial ordering constraints are satisfied."""
    for index, trial in enumerate(schedule):
        prior = schedule[:index]
        for field in ("information_condition", "skew_condition", "gamble_side"):
            if not _max_run_ok(prior, trial, field):
                return False
        if prior:
            signature = ("skew_condition", "information_condition", "gamble_side")
            if all(prior[-1][field] == trial[field] for field in signature):
                return False
    first_block = schedule[:8]
    for skew in SKEW_CONDITIONS:
        visible = next(i for i, trial in enumerate(first_block) if trial["skew_condition"] == skew and trial["information_condition"] == "risk")
        hidden = next(i for i, trial in enumerate(first_block) if trial["skew_condition"] == skew and trial["information_condition"] == "hidden_probability")
        if visible > hidden:
            return False
    return True


def _block_candidate(block_number: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for skew, info in CELLS:
        for side in ("left", "right"):
            records.append(
                {
                    "mini_block": block_number,
                    "skew_condition": skew,
                    "information_condition": info,
                    "gamble_side": side,
                    "safe_side": "right" if side == "left" else "left",
                }
            )
    return records


def _valid_append(schedule: Sequence[Mapping[str, Any]], trial: Mapping[str, Any]) -> bool:
    for field in ("information_condition", "skew_condition", "gamble_side"):
        if not _max_run_ok(schedule, trial, field):
            return False
    if schedule and all(
        schedule[-1][field] == trial[field]
        for field in ("skew_condition", "information_condition", "gamble_side")
    ):
        return False
    return True


def _order_block(
    records: List[Dict[str, Any]],
    existing: Sequence[Mapping[str, Any]],
    rng: np.random.Generator,
    first: bool,
) -> Optional[List[Dict[str, Any]]]:
    """Randomized depth-first ordering for one eight-trial mini-block."""
    def search(prefix: List[Dict[str, Any]], remaining: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not remaining:
            return prefix
        indices = list(rng.permutation(len(remaining)))
        for index in indices:
            trial = remaining[index]
            combined = list(existing) + prefix
            if not _valid_append(combined, trial):
                continue
            if first and trial["information_condition"] == "hidden_probability":
                cue_seen_visible = any(
                    item["skew_condition"] == trial["skew_condition"]
                    and item["information_condition"] == "risk"
                    for item in prefix
                )
                if not cue_seen_visible:
                    continue
            result = search(prefix + [trial], remaining[:index] + remaining[index + 1 :])
            if result is not None:
                return result
        return None

    return search([], records)


def generate_schedule(
    config: Mapping[str, Any], subject: str, session: str, run: int, seed: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Dict[str, Any]]]:
    """Generate the complete balanced schedule before presentation."""
    actual_seed = derive_seed(subject, session, run) if seed is None else int(seed)
    rng = np.random.default_rng(actual_seed)
    n_blocks = int(config["task"]["trials"]) // 8
    mapping = counterbalance_cues(subject, run, config["cue_library"])
    schedule: List[Dict[str, Any]] = []
    for block in range(1, n_blocks + 1):
        ordered = _order_block(_block_candidate(block), schedule, rng, first=(block == 1))
        if ordered is None:
            raise RuntimeError(f"Unable to order mini-block {block} for seed {actual_seed}")
        schedule.extend(ordered)

    gambles = config["gambles"]
    mapping_label = ";".join(f"{cue['id']}={skew}" for skew, cue in mapping.items())
    for index, trial in enumerate(schedule, start=1):
        skew = trial["skew_condition"]
        cue = mapping[skew]
        gamble = gambles[skew]
        trial.update(
            {
                "trial_number": index,
                "practice": False,
                "cue_id": cue["id"],
                "cue_color": cue["color_name"],
                "cue_color_rgb": list(cue["color"]),
                "cue_shape": cue["shape"],
                "cue_mapping": mapping_label,
                "p_gain_actual": float(gamble["p_gain"]),
                "p_gain_displayed": float(gamble["p_gain"])
                if trial["information_condition"] == "risk"
                else None,
                "gain_amount": float(gamble["gain_amount"]),
                "loss_amount": float(gamble["loss_amount"]),
                "safe_amount": float(gambles["safe_amount"]),
            }
        )
    if not schedule_constraints_hold(schedule):
        raise AssertionError("Internal schedule constraint failure")
    return schedule, actual_seed, mapping


def cell_counts(schedule: Sequence[Mapping[str, Any]]) -> Counter:
    """Count trials per factorial cell."""
    return Counter((trial["skew_condition"], trial["information_condition"]) for trial in schedule)

