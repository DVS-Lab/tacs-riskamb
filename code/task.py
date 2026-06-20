"""Nonblocking Pygame run controller for the risk–ambiguity task."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pygame

from data_writer import RunPaths, TrialDataWriter, update_json, utc_now
from instructions import comprehension_check, practice_schedule, show_instructions
from learning import LearningTracker
from panas import administer_panas
from stimuli import StimulusRenderer
from timing import jitter_ms
from triggers import LSLStartListener, MarkerLogger


class TaskAbort(RuntimeError):
    """Participant or operator requested a safe early exit."""


@dataclass
class Response:
    responded: bool
    key: str = ""
    side: str = ""
    choice: str = "miss"
    rt_ms: Optional[float] = None


class RiskAmbiguityTask:
    """Present practice, one experimental run, and post-run measures."""

    def __init__(
        self,
        screen: pygame.Surface,
        config: Mapping[str, Any],
        schedule: Sequence[Mapping[str, Any]],
        cue_mapping: Mapping[str, Mapping[str, Any]],
        rng: np.random.Generator,
        identifiers: Mapping[str, Any],
        paths: RunPaths,
        auto_respond: bool = False,
        skip_instructions: bool = False,
    ) -> None:
        self.screen = screen
        self.config = config
        self.schedule = [dict(trial) for trial in schedule]
        self.cue_mapping = {key: dict(value) for key, value in cue_mapping.items()}
        self.rng = rng
        self.ids = dict(identifiers)
        self.paths = paths
        self.auto_respond = auto_respond
        self.skip_instructions = skip_instructions
        self.renderer = StimulusRenderer(screen, config)
        self.marker = MarkerLogger(paths.markers, config["triggers"])
        self.start_listener = LSLStartListener(config["triggers"])
        self.frame_rate = int(config["timing_ms"].get("frame_rate", 60))
        self.clock = pygame.time.Clock()
        self.run_start = time.perf_counter()
        self.cumulative_total = 0.0
        self.completed_rows: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def _elapsed_ms(self) -> float:
        return (time.perf_counter() - self.run_start) * 1000.0

    def _events_abort(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
        return False

    def _wait_ms(self, duration_ms: float) -> bool:
        """Wait while pumping Pygame events; return a dropped-frame warning."""
        started = time.perf_counter()
        warning = False
        frame_budget = 1000.0 / max(1, self.frame_rate)
        while (time.perf_counter() - started) * 1000.0 < duration_ms:
            if self._events_abort():
                raise TaskAbort("Escape/quit during timed state")
            frame_ms = self.clock.tick(self.frame_rate)
            warning = warning or frame_ms > 2.0 * frame_budget
        return warning

    def _condition_marker(self, trial: Mapping[str, Any]) -> str:
        skew = str(trial["skew_condition"])
        info = str(trial["information_condition"])
        return f"{skew}_{info}_onset"

    def _collect_response(self, trial: Mapping[str, Any]) -> Response:
        responses = self.config["responses"]
        left_name = str(responses["left_key"]).lower()
        right_name = str(responses["right_key"]).lower()
        key_map = {
            pygame.key.key_code(left_name): ("left", left_name),
            pygame.key.key_code(right_name): ("right", right_name),
        }
        if responses.get("allow_button_box"):
            for name, side in (
                (str(responses["button_box_left_key"]), "left"),
                (str(responses["button_box_right_key"]), "right"),
            ):
                key_map[pygame.key.key_code(name)] = (side, name)

        deadline = float(self.config["timing_ms"]["choice_deadline"])
        started = time.perf_counter()
        auto_side = "left" if self.rng.random() < 0.5 else "right"
        auto_rt = float(self.rng.integers(*[int(value) for value in self.config["task"]["auto_response_rt_ms"]]))
        while (time.perf_counter() - started) * 1000.0 < deadline:
            elapsed = (time.perf_counter() - started) * 1000.0
            if self.auto_respond and elapsed >= auto_rt:
                choice = "gamble" if auto_side == trial["gamble_side"] else "safe"
                return Response(True, f"auto_{auto_side}", auto_side, choice, elapsed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    raise TaskAbort("Escape/quit during choice")
                if event.type == pygame.KEYDOWN and event.key in key_map:
                    side, key_name = key_map[event.key]
                    choice = "gamble" if side == trial["gamble_side"] else "safe"
                    return Response(True, key_name, side, choice, elapsed)
            self.clock.tick(self.frame_rate)
        return Response(False)

    def _base_row(self, trial: Mapping[str, Any]) -> Dict[str, Any]:
        row = dict(trial)
        row.update(
            {
                "subject_id": self.ids["subject_id"],
                "session": self.ids["session"],
                "run": self.ids["run"],
                "task_version": self.ids["task_version"],
                "git_commit": self.ids["git_commit"],
                "configuration_file": self.ids["configuration_file"],
                "random_seed": self.ids["random_seed"],
                "timestamp_utc": utc_now(),
            }
        )
        return row

    def run_trial(
        self,
        trial: Mapping[str, Any],
        writer: TrialDataWriter,
        learning: LearningTracker,
        emit_markers: bool = True,
    ) -> Dict[str, Any]:
        """Run one state sequence and durably append the resulting row."""
        timing = self.config["timing_ms"]
        fixation_duration = jitter_ms(timing["fixation"], self.rng)
        pre_feedback_delay = jitter_ms(timing["pre_feedback"], self.rng)
        iti_duration = jitter_ms(timing["iti"], self.rng)
        row = self._base_row(trial)
        row.update(learning.before(trial))
        row["run_elapsed_at_trial_start_ms"] = self._elapsed_ms()
        dropped = False
        if emit_markers:
            self.marker.send("trial_start", f"trial={trial['trial_number']}")

        row["fixation_onset_ms"] = self._elapsed_ms()
        self.renderer.draw_fixation()
        pygame.display.flip()
        dropped |= self._wait_ms(fixation_duration)

        # Clearing immediately before onset prevents responses carried from prior states.
        pygame.event.clear()
        self.renderer.draw_choice(trial)
        pygame.display.flip()
        row["choice_onset_ms"] = self._elapsed_ms()
        if emit_markers:
            self.marker.send(self._condition_marker(trial), f"trial={trial['trial_number']}")
        response = self._collect_response(trial)
        row["response_time_ms"] = self._elapsed_ms() if response.responded else None

        if response.responded:
            if emit_markers:
                self.marker.send("response", f"trial={trial['trial_number']};side={response.side}")
                self.marker.send("gamble_selected" if response.choice == "gamble" else "safe_selected", f"trial={trial['trial_number']}")
            self.renderer.draw_choice(trial, selected=response.side)
            pygame.display.flip()
            dropped |= self._wait_ms(float(timing["selection_highlight"]))

        self.renderer.clear()
        pygame.display.flip()
        dropped |= self._wait_ms(pre_feedback_delay)

        outcome_type = str(trial["outcome_preassigned"])
        realized = float(trial["gain_amount"] if outcome_type == "gain" else trial["loss_amount"])
        chosen = realized if response.choice == "gamble" else 0.0 if response.choice == "safe" else None
        if response.responded and chosen is not None:
            self.cumulative_total += chosen
        row["feedback_onset_ms"] = self._elapsed_ms()
        if emit_markers:
            feedback_label = "feedback_miss" if not response.responded else f"feedback_{outcome_type}"
            self.marker.send(feedback_label, f"trial={trial['trial_number']};outcome={outcome_type}")
        self.renderer.draw_feedback(trial, response.choice, response.responded)
        if (
            self.config["task"].get("display_cumulative_total", False)
            and self.config["task"].get("payoff_mode") == "cumulative"
        ):
            self.renderer.text(
                f"Running total: ${self.cumulative_total:.2f}",
                (self.renderer.width // 2, int(self.renderer.height * 0.78)),
                self.renderer.font_small,
            )
        pygame.display.flip()
        dropped |= self._wait_ms(float(timing["feedback"]))

        self.renderer.clear()
        pygame.display.flip()
        dropped |= self._wait_ms(iti_duration)
        row["trial_end_ms"] = self._elapsed_ms()

        counterfactual = bool(
            response.choice != "gamble" and self.config["task"].get("counterfactual_feedback", True)
        )
        outcome_shown = response.choice == "gamble" or counterfactual
        row.update(
            {
                "response_key": response.key,
                "response_side": response.side,
                "choice": response.choice,
                "gamble_selected": response.choice == "gamble",
                "responded": response.responded,
                "reaction_time_ms": response.rt_ms,
                "response_deadline_ms": timing["choice_deadline"],
                "realized_outcome_type": outcome_type,
                "realized_outcome_amount": realized,
                "chosen_outcome_amount": chosen,
                "counterfactual_outcome_shown": counterfactual,
                "cumulative_total": round(self.cumulative_total, 2),
                "bonus_eligible": response.responded,
                "fixation_duration_ms": fixation_duration,
                "pre_feedback_delay_ms": pre_feedback_delay,
                "iti_duration_ms": iti_duration,
                "dropped_frame_warning": dropped,
            }
        )
        writer.append(row)
        learning.observe(trial, outcome_shown=outcome_shown)
        if not trial.get("practice"):
            self.completed_rows.append(row)
        return row

    def _wait_for_start(self) -> None:
        mode = str(self.config["triggers"].get("start_mode", "space"))
        scanner_name = str(self.config["responses"].get("scanner_trigger_key", "5"))
        scanner_key = pygame.key.key_code(scanner_name)
        if self.auto_respond:
            return
        self.renderer.clear()
        self.renderer.text("Waiting to begin", (self.renderer.width // 2, int(self.renderer.height * 0.40)), self.renderer.font_large)
        prompt = {
            "space": "Press SPACE to begin",
            "scanner": f"Press scanner trigger ({scanner_name}) or SPACE",
            "lsl": "Waiting for LSL marker (SPACE is manual fallback)",
        }.get(mode, "Press SPACE to begin")
        self.renderer.text(prompt, (self.renderer.width // 2, int(self.renderer.height * 0.60)), self.renderer.font_small)
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    raise TaskAbort("Abort while waiting for run start")
                if event.type == pygame.KEYDOWN and (
                    event.key == pygame.K_SPACE or (mode == "scanner" and event.key == scanner_key)
                ):
                    return
            if mode == "lsl" and self.start_listener.poll():
                return
            self.clock.tick(self.frame_rate)

    def _belief_probes(self) -> Optional[List[Dict[str, Any]]]:
        order = list(self.cue_mapping.keys())
        self.rng.shuffle(order)
        results: List[Dict[str, Any]] = []
        for skew in order:
            cue = self.cue_mapping[skew]
            example = {
                "cue_id": cue["id"], "cue_color_rgb": cue["color"],
                "cue_shape": cue["shape"], "cue_color": cue["color_name"],
            }
            estimate = 50
            confidence = 5
            for stage in ("probability", "confidence"):
                if self.auto_respond:
                    if stage == "probability":
                        estimate = int(round(float(self.config["gambles"][skew]["p_gain"]) * 100))
                    continue
                confirmed = False
                while not confirmed:
                    self.renderer.draw_belief_probe(example, estimate, confidence, stage)
                    pygame.display.flip()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                            return None
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_LEFT:
                                if stage == "probability":
                                    estimate = max(0, estimate - 5)
                                else:
                                    confidence = max(1, confidence - 1)
                            elif event.key == pygame.K_RIGHT:
                                if stage == "probability":
                                    estimate = min(100, estimate + 5)
                                else:
                                    confidence = min(9, confidence + 1)
                            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                                confirmed = True
                    self.clock.tick(self.frame_rate)
            results.append(
                {
                    "cue_id": cue["id"], "cue_color": cue["color_name"],
                    "cue_shape": cue["shape"], "actual_mapping": skew,
                    "estimated_gain_probability_percent": estimate,
                    "confidence_1_to_9": confidence,
                }
            )
        return results

    def _payoff_summary(self) -> Dict[str, Any]:
        valid = [row for row in self.completed_rows if row["responded"]]
        mode = str(self.config["task"]["payoff_mode"])
        result: Dict[str, Any] = {
            "payoff_mode": mode,
            "valid_trial_numbers": [row["trial_number"] for row in valid],
            "cumulative_chosen_outcome": round(self.cumulative_total, 2),
        }
        if mode == "random_trial" and valid:
            selected = valid[int(self.rng.integers(0, len(valid)))]
            result.update(
                {
                    "bonus_selected_trial": selected["trial_number"],
                    "bonus_selected_choice": selected["choice"],
                    "bonus_raw_outcome": selected["chosen_outcome_amount"],
                }
            )
        elif mode == "cumulative":
            result["bonus_raw_outcome"] = round(self.cumulative_total, 2)
        else:
            result["bonus_raw_outcome"] = None
        return result

    def run(self) -> Dict[str, Any]:
        """Run all enabled phases and return run-level summary data."""
        comprehension: Optional[Dict[str, Any]] = None
        if not self.skip_instructions:
            later_run = int(self.ids["run"]) > 1
            if not show_instructions(self.renderer, self.auto_respond, reminder=later_run):
                raise TaskAbort("Instructions aborted")
            if not later_run and self.config["task"].get("comprehension_check_enabled"):
                comprehension = comprehension_check(self.renderer, self.auto_respond)
                if comprehension is None:
                    raise TaskAbort("Comprehension check aborted")

        if self.config["task"].get("practice_enabled"):
            practice_writer = TrialDataWriter(self.paths.practice_events)
            try:
                tracker = LearningTracker()
                self.run_start = time.perf_counter()
                for trial in practice_schedule(self.config, self.rng):
                    self.run_trial(trial, practice_writer, tracker, emit_markers=False)
            finally:
                practice_writer.close()

        self._wait_for_start()
        self.run_start = time.perf_counter()
        self.marker.send("run_start", f"run={self.ids['run']}")
        if self.config["task"].get("start_buffer_enabled"):
            self.renderer.draw_fixation()
            pygame.display.flip()
            self._wait_ms(float(self.config["timing_ms"]["start_buffer"]))

        writer = TrialDataWriter(self.paths.events)
        try:
            tracker = LearningTracker()
            for trial in self.schedule:
                self.run_trial(trial, writer, tracker, emit_markers=True)
        finally:
            writer.close()
        self.marker.send("run_end", f"run={self.ids['run']}")
        timed_duration_ms = self._elapsed_ms()

        beliefs = None
        if self.config["task"].get("belief_probe_enabled"):
            beliefs = self._belief_probes()
            if beliefs is None:
                raise TaskAbort("Belief probe aborted")
        panas = None
        if self.config["task"].get("panas_enabled"):
            panas = administer_panas(self.renderer, self.auto_respond)
            if panas is None:
                raise TaskAbort("PANAS aborted")

        self.summary = {
            "status": "complete",
            "completed_utc": utc_now(),
            "timed_run_duration_ms_including_start_buffer": timed_duration_ms,
            "completed_trials": len(self.completed_rows),
            "comprehension": comprehension,
            "belief_probes": beliefs,
            "panas": panas,
            "payoff": self._payoff_summary(),
        }
        update_json(self.paths.summary, self.summary)
        return self.summary

    def close(self) -> None:
        self.marker.close()
