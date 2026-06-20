import csv

import pytest

from data_writer import EVENT_COLUMNS, TrialDataWriter, create_run_paths


def test_all_required_columns_are_present():
    required = {
        "subject_id", "trial_number", "information_condition", "outcome_preassigned",
        "reaction_time_ms", "feedback_onset_ms", "prior_cue_exposures",
        "most_recent_realized_outcome_for_cue",
    }
    assert required <= set(EVENT_COLUMNS)


def test_partial_data_survive_intentional_abort(tmp_path):
    paths = create_run_paths(tmp_path, "001", "1", 1)
    with pytest.raises(RuntimeError):
        with TrialDataWriter(paths.events) as writer:
            writer.append({"subject_id": "001", "trial_number": 1})
            raise RuntimeError("intentional")
    with paths.events.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["trial_number"] == "1"


def test_output_collision_never_overwrites(tmp_path):
    first = create_run_paths(tmp_path, "001", "1", 1)
    first.events.write_text("sentinel", encoding="utf-8")
    second = create_run_paths(tmp_path, "001", "1", 1)
    assert first.events != second.events
    assert first.events.read_text(encoding="utf-8") == "sentinel"

