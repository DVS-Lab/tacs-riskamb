"""Crash-resistant task output and complete events schema."""

from __future__ import annotations

import csv
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from learning import LEARNING_COLUMNS


IDENTIFICATION_COLUMNS = [
    "subject_id", "session", "run", "task_version", "git_commit",
    "configuration_file", "random_seed", "timestamp_utc",
]
DESIGN_COLUMNS = [
    "trial_number", "mini_block", "practice", "skew_condition",
    "information_condition", "cue_id", "cue_color", "cue_shape",
    "cue_mapping", "gamble_side", "safe_side", "p_gain_actual",
    "p_gain_displayed", "gain_amount", "loss_amount", "safe_amount",
    "outcome_preassigned",
]
RESPONSE_COLUMNS = [
    "response_key", "response_side", "choice", "gamble_selected", "responded",
    "reaction_time_ms", "response_deadline_ms",
]
OUTCOME_COLUMNS = [
    "realized_outcome_type", "realized_outcome_amount", "chosen_outcome_amount",
    "counterfactual_outcome_shown", "cumulative_total", "bonus_eligible",
]
TIMING_COLUMNS = [
    "run_elapsed_at_trial_start_ms", "fixation_onset_ms", "choice_onset_ms",
    "response_time_ms", "feedback_onset_ms", "trial_end_ms",
    "fixation_duration_ms", "pre_feedback_delay_ms", "iti_duration_ms",
    "dropped_frame_warning",
]
EVENT_COLUMNS = (
    IDENTIFICATION_COLUMNS + DESIGN_COLUMNS + RESPONSE_COLUMNS + OUTCOME_COLUMNS
    + TIMING_COLUMNS + LEARNING_COLUMNS
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def git_commit(repo_root: Path) -> str:
    """Return the current commit identifier, or ``unknown`` outside Git."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@dataclass(frozen=True)
class RunPaths:
    """All paths belonging to one uniquely named run."""

    events: Path
    planned_schedule: Path
    metadata: Path
    config: Path
    markers: Path
    summary: Path
    practice_events: Path


def create_run_paths(base_dir: Path, subject: str, session: str, run: int) -> RunPaths:
    """Reserve a collision-free BIDS-inspired filename group."""
    subject_dir = Path(base_dir) / f"sub-{subject}"
    subject_dir.mkdir(parents=True, exist_ok=True)
    base = f"sub-{subject}_ses-{session}_run-{int(run):02d}_task-riskambiguity"
    stem = base
    counter = 0
    while (subject_dir / f"{stem}_events.csv").exists():
        counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        stem = f"{base}_{timestamp}_{counter}"
    events = subject_dir / f"{stem}_events.csv"
    # Exclusive creation reserves the core filename against concurrent launches.
    with events.open("x", encoding="utf-8", newline=""):
        pass
    return RunPaths(
        events=events,
        planned_schedule=subject_dir / f"{stem}_planned.csv",
        metadata=subject_dir / f"{stem}_metadata.json",
        config=subject_dir / f"{stem}_config.json",
        markers=subject_dir / f"{stem}_markers.csv",
        summary=subject_dir / f"{stem}_summary.json",
        practice_events=subject_dir / f"{stem}_practice.csv",
    )


def write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    """Write formatted JSON without replacing an existing file."""
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def update_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace run-owned metadata after initial reservation."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def write_schedule(path: Path, schedule: Iterable[Mapping[str, Any]]) -> None:
    """Save the complete plan before trial presentation."""
    rows = list(schedule)
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with Path(path).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())


class TrialDataWriter:
    """Append and force each completed row to durable storage."""

    def __init__(self, path: Path, columns: Optional[List[str]] = None) -> None:
        self.path = Path(path)
        self.columns = columns or EVENT_COLUMNS
        self._stream = self.path.open("a", encoding="utf-8", newline="", buffering=1)
        self._writer = csv.DictWriter(self._stream, fieldnames=self.columns, extrasaction="ignore")
        if self.path.stat().st_size == 0:
            self._writer.writeheader()
            self._sync()

    def _sync(self) -> None:
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def append(self, row: Mapping[str, Any]) -> None:
        self._writer.writerow({column: row.get(column) for column in self.columns})
        self._sync()

    def close(self) -> None:
        if not self._stream.closed:
            self._sync()
            self._stream.close()

    def __enter__(self) -> "TrialDataWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

