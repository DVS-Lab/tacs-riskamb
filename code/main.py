"""Command-line entry point for the Pygame risk–ambiguity learning task."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pygame

from config import DEFAULT_CONFIG, REPO_ROOT, TEST_CONFIG, load_config, resolved_output_dir, validate_config
from data_writer import create_run_paths, git_commit, update_json, utc_now, write_json_exclusive, write_schedule
from outcome_generation import assign_stratified_outcomes
from setup_screen import experimenter_setup
from task import RiskAmbiguityTask, TaskAbort
from trial_generation import derive_seed, generate_schedule


def normalize_identifier(value: str, prefix: str) -> str:
    """Strip an optional BIDS prefix and reject unsafe identifier characters."""
    cleaned = str(value).strip()
    if cleaned.startswith(prefix + "-"):
        cleaned = cleaned[len(prefix) + 1 :]
    if not cleaned or not re.fullmatch(r"[A-Za-z0-9_-]+", cleaned):
        raise ValueError(f"Invalid {prefix} identifier: {value!r}")
    return cleaned


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the risk–ambiguity learning task")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--subject")
    parser.add_argument("--session", default=None)
    parser.add_argument("--run", type=int, default=None)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--test", action="store_true", help="Use the eight-trial fast configuration")
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--display", type=int)
    parser.add_argument("--trigger-mode", choices=["space", "scanner", "lsl"])
    parser.add_argument("--auto-respond", action="store_true", help="Development only; writes under data/development")
    parser.add_argument("--skip-instructions", action="store_true", help="Development/test convenience")
    parser.add_argument("--data-dir", type=Path, help="Override output directory")
    return parser.parse_args(argv)


def _open_screen(config: Dict[str, Any]) -> pygame.Surface:
    pygame.init()
    pygame.font.init()
    display = config["display"]
    flags = pygame.FULLSCREEN if display.get("fullscreen") else 0
    size = (0, 0) if flags else (int(display["width"]), int(display["height"]))
    try:
        return pygame.display.set_mode(size, flags, display=int(display.get("display_index", 0)))
    except (pygame.error, TypeError):
        return pygame.display.set_mode((int(display["width"]), int(display["height"])))


def run_from_args(args: argparse.Namespace) -> int:
    config_path = TEST_CONFIG if args.test else args.config
    config = load_config(config_path)
    if args.windowed:
        config["display"]["fullscreen"] = False
    if args.display is not None:
        config["display"]["display_index"] = args.display
    if args.trigger_mode:
        config["triggers"]["start_mode"] = args.trigger_mode
    if args.data_dir:
        config["paths"]["data_dir"] = str(args.data_dir.resolve())
    validate_config(config)

    screen = _open_screen(config)
    subject, session, run = args.subject, args.session, args.run
    if subject is None or session is None or run is None:
        setup = experimenter_setup(
            screen,
            {
                "subject": subject, "session": session or "1", "run": run or 1,
                "display_index": config["display"].get("display_index", 0),
                "fullscreen": config["display"].get("fullscreen", False),
                "trigger_mode": config["triggers"].get("start_mode", "space"),
                "test_mode": args.test,
            },
        )
        if setup is None:
            pygame.quit()
            return 2
        subject, session, run = setup["subject"], setup["session"], int(setup["run"])
        config["display"]["display_index"] = setup["display_index"]
        config["display"]["fullscreen"] = setup["fullscreen"]
        config["triggers"]["start_mode"] = setup["trigger_mode"]
        if setup["test_mode"] and not args.test:
            config = load_config(TEST_CONFIG)
            config["display"]["fullscreen"] = setup["fullscreen"]
            config["display"]["display_index"] = setup["display_index"]
            config["triggers"]["start_mode"] = setup["trigger_mode"]
        pygame.display.quit()
        screen = _open_screen(config)

    subject_id = normalize_identifier(str(subject), "sub")
    session_id = normalize_identifier(str(session), "ses")
    if int(run) < 1:
        raise ValueError("run must be at least 1")
    seed = derive_seed(subject_id, session_id, int(run)) if args.seed is None else int(args.seed)
    schedule, seed, mapping = generate_schedule(config, subject_id, session_id, int(run), seed)
    rng = np.random.default_rng(seed)
    schedule = assign_stratified_outcomes(schedule, rng)

    output_dir = Path(args.data_dir).resolve() if args.data_dir else resolved_output_dir(config, args.auto_respond)
    paths = create_run_paths(output_dir, subject_id, session_id, int(run))
    identifiers = {
        "subject_id": subject_id,
        "session": session_id,
        "run": int(run),
        "task_version": config["task"]["version"],
        "git_commit": git_commit(REPO_ROOT),
        "configuration_file": config["_config_file"],
        "random_seed": seed,
    }
    metadata = {
        **identifiers,
        "status": "initialized",
        "created_utc": utc_now(),
        "development_auto_response": bool(args.auto_respond),
        "cue_mapping": mapping,
        "output_files": {key: str(value) for key, value in paths.__dict__.items()},
        "pylsl_required": False,
    }
    # All reconstruction artifacts exist before participant-facing trial one.
    write_schedule(paths.planned_schedule, schedule)
    write_json_exclusive(paths.config, config)
    write_json_exclusive(paths.metadata, metadata)
    write_json_exclusive(paths.summary, {"status": "initialized", "created_utc": utc_now()})

    task: Optional[RiskAmbiguityTask] = None
    try:
        pygame.display.set_caption("Risk–Ambiguity Learning Task")
        task = RiskAmbiguityTask(
            screen, config, schedule, mapping, rng, identifiers, paths,
            auto_respond=args.auto_respond, skip_instructions=args.skip_instructions,
        )
        summary = task.run()
        metadata.update({"status": "complete", "completed_utc": utc_now(), "summary": summary})
        update_json(paths.metadata, metadata)
        return 0
    except TaskAbort as error:
        metadata.update({"status": "aborted", "aborted_utc": utc_now(), "abort_reason": str(error)})
        update_json(paths.metadata, metadata)
        update_json(paths.summary, {"status": "aborted", "reason": str(error), "timestamp_utc": utc_now()})
        return 130
    except Exception as error:
        metadata.update(
            {
                "status": "error", "error_utc": utc_now(),
                "error_type": type(error).__name__, "error_message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
        update_json(paths.metadata, metadata)
        update_json(paths.summary, {"status": "error", "error": str(error), "timestamp_utc": utc_now()})
        raise
    finally:
        if task is not None:
            task.close()
        pygame.quit()


def main() -> int:
    try:
        return run_from_args(parse_args())
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Configuration/setup error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
