"""Configuration loading, recursive overrides, and validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Mapping


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "default.json"
TEST_CONFIG = REPO_ROOT / "config" / "test.json"


def _merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into a copied base mapping."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key == "extends":
            continue
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(dict(result[key]), value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: Path | str = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Load a JSON configuration, resolving an optional relative ``extends``."""
    config_path = Path(path).expanduser().resolve()
    with config_path.open(encoding="utf-8") as stream:
        raw = json.load(stream)
    if "extends" in raw:
        parent = (config_path.parent / raw["extends"]).resolve()
        config = _merge(load_config(parent), raw)
    else:
        config = raw
    config["_config_file"] = str(config_path)
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    """Fail early when design settings cannot satisfy task invariants."""
    trials = int(config["task"]["trials"])
    block_size = int(config["task"]["mini_block_size"])
    if trials <= 0 or trials % block_size or block_size != 8:
        raise ValueError("task.trials must be a positive multiple of the 8-trial mini-block")
    gambles = config["gambles"]
    if "negative_skew" in gambles:
        raise ValueError("Negative-skew gambles are not part of this task")
    for name in ("symmetric", "positive_skew"):
        probability = float(gambles[name]["p_gain"])
        if not 0.0 < probability < 1.0:
            raise ValueError(f"{name}.p_gain must be strictly between 0 and 1")
        if float(gambles[name]["gain_amount"]) <= 0:
            raise ValueError(f"{name}.gain_amount must be positive")
        if float(gambles[name]["loss_amount"]) >= 0:
            raise ValueError(f"{name}.loss_amount must be negative")
    if config["task"]["payoff_mode"] not in {"random_trial", "cumulative", "points_only"}:
        raise ValueError("Unsupported payoff mode")
    if len(config["cue_library"]) < 2 or len(config["cue_library"]) % 2:
        raise ValueError("cue_library must contain complete pairs")


def resolved_output_dir(config: Mapping[str, Any], development: bool = False) -> Path:
    """Resolve the configured data directory relative to the repository root."""
    path = Path(config["paths"]["data_dir"])
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path / "development" if development else path

