"""Participant instructions, comprehension check, and later-run reminder."""

from __future__ import annotations

import textwrap
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pygame

from stimuli import StimulusRenderer


INSTRUCTION_PAGES = [
    [
        "Lottery choices",
        "On each trial, choose between a lottery and a guaranteed $0.",
        "The lottery can produce the gain or loss printed on screen.",
        "Press F for the left option and J for the right option.",
        "Respond before the deadline.",
    ],
    [
        "Learning from visual cues",
        "Every lottery has a colored shape around it.",
        "The cue can help you learn how that lottery tends to behave.",
        "Some trials show the exact chance of a gain.",
        "Other trials cover the probability with a gray ? mask.",
        "The possible gain and loss stay visible in both cases.",
    ],
    [
        "Feedback and payment",
        "The lottery outcome is shown after every trial, even if you choose $0.",
        "Use that feedback to learn about each cue.",
        "Only the option you choose affects your earnings.",
        "One or more decisions may affect your bonus, depending on the payment rule.",
        "Use LEFT/RIGHT or SPACE to move through these pages.",
    ],
]

REMINDER = [
    "Run reminder",
    "F = left     J = right",
    "Choose between the lottery and guaranteed $0 before the deadline.",
    "A gray ? hides probability only; gain and loss amounts remain visible.",
    "Lottery outcomes appear after every trial. Use the cues and feedback to learn.",
]

COMPREHENSION = [
    {
        "question": "Which keys choose the left and right options?",
        "answers": ["F and J", "G and H", "Arrow keys"],
        "correct": 0,
        "review_page": 0,
    },
    {
        "question": "What does the gray ? mask mean?",
        "answers": ["The probability is hidden", "The amounts are unknown", "The trial does not count"],
        "correct": 0,
        "review_page": 1,
    },
    {
        "question": "What does the guaranteed option pay?",
        "answers": ["Exactly $0", "A hidden amount", "The lottery average"],
        "correct": 0,
        "review_page": 0,
    },
]


def _draw_lines(renderer: StimulusRenderer, lines: Sequence[str], footer: str = "SPACE / RIGHT continue") -> None:
    renderer.clear()
    top = int(renderer.height * 0.16)
    spacing = int(renderer.height * 0.10)
    for index, line in enumerate(lines):
        font = renderer.font_large if index == 0 else renderer.font_small
        wrapped = [line] if index == 0 else textwrap.wrap(line, width=74) or [""]
        for part_index, part in enumerate(wrapped):
            renderer.text(part, (renderer.width // 2, top + index * spacing + part_index * int(spacing * 0.45)), font)
    renderer.text(footer, (renderer.width // 2, int(renderer.height * 0.91)), renderer.font_small, renderer.highlight)
    pygame.display.flip()


def _wait_for_navigation(auto_respond: bool = False) -> str:
    if auto_respond:
        return "next"
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "abort"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "abort"
                if event.key == pygame.K_LEFT:
                    return "back"
                if event.key in (pygame.K_RIGHT, pygame.K_SPACE, pygame.K_RETURN):
                    return "next"
        clock.tick(60)


def show_instructions(renderer: StimulusRenderer, auto_respond: bool = False, reminder: bool = False) -> bool:
    """Show navigable full instructions or a concise later-run reminder."""
    pages = [REMINDER] if reminder else INSTRUCTION_PAGES
    index = 0
    while index < len(pages):
        _draw_lines(renderer, pages[index])
        action = _wait_for_navigation(auto_respond)
        if action == "abort":
            return False
        if action == "back":
            index = max(0, index - 1)
        else:
            index += 1
    return True


def _ask_question(renderer: StimulusRenderer, item: Mapping[str, Any], auto_respond: bool) -> Optional[int]:
    if auto_respond:
        return int(item["correct"])
    renderer.clear()
    renderer.text("Quick check", (renderer.width // 2, int(renderer.height * 0.18)), renderer.font_large)
    renderer.text(str(item["question"]), (renderer.width // 2, int(renderer.height * 0.34)), renderer.font_medium)
    for index, answer in enumerate(item["answers"], start=1):
        renderer.text(f"{index}. {answer}", (renderer.width // 2, int(renderer.height * (0.47 + 0.10 * index))), renderer.font_small)
    pygame.display.flip()
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return None
            if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_3:
                return event.key - pygame.K_1
        clock.tick(60)


def comprehension_check(renderer: StimulusRenderer, auto_respond: bool = False) -> Optional[Dict[str, Any]]:
    """Require all answers; review the relevant page after each error."""
    attempts = 0
    errors = 0
    for item in COMPREHENSION:
        while True:
            attempts += 1
            response = _ask_question(renderer, item, auto_respond)
            if response is None:
                return None
            if response == item["correct"]:
                break
            errors += 1
            _draw_lines(renderer, INSTRUCTION_PAGES[int(item["review_page"])], "Review this page, then press SPACE")
            if _wait_for_navigation(auto_respond) == "abort":
                return None
    return {"passed": True, "attempts": attempts, "errors": errors}


def practice_schedule(config: Mapping[str, Any], rng: Any) -> List[Dict[str, Any]]:
    """Create four trials with nonexperimental cues, amounts, and probabilities."""
    records: List[Dict[str, Any]] = []
    cue_specs = {
        "practice_symmetric": {"id": "practice_wave", "color_name": "lime", "color": [126, 205, 92], "shape": "pentagon"},
        "practice_skewed": {"id": "practice_cross", "color_name": "silver", "color": [192, 198, 207], "shape": "triangle"},
    }
    combinations = [
        ("practice_symmetric", "risk"),
        ("practice_symmetric", "hidden_probability"),
        ("practice_skewed", "risk"),
        ("practice_skewed", "hidden_probability"),
    ]
    rng.shuffle(combinations)
    # Guarantee one visible exposure precedes hidden exposure for each practice cue.
    combinations.sort(key=lambda pair: (pair[0], pair[1] == "hidden_probability"))
    for index, (gamble_name, information) in enumerate(combinations, start=1):
        gamble = config["gambles"][gamble_name]
        cue = cue_specs[gamble_name]
        side = "left" if index % 2 else "right"
        outcome = "gain" if rng.random() < float(gamble["p_gain"]) else "loss"
        records.append(
            {
                "trial_number": index,
                "mini_block": 0,
                "practice": True,
                "skew_condition": gamble_name,
                "information_condition": information,
                "cue_id": cue["id"],
                "cue_color": cue["color_name"],
                "cue_color_rgb": cue["color"],
                "cue_shape": cue["shape"],
                "cue_mapping": "practice_only",
                "gamble_side": side,
                "safe_side": "right" if side == "left" else "left",
                "p_gain_actual": float(gamble["p_gain"]),
                "p_gain_displayed": float(gamble["p_gain"]) if information == "risk" else None,
                "gain_amount": float(gamble["gain_amount"]),
                "loss_amount": float(gamble["loss_amount"]),
                "safe_amount": float(config["gambles"]["safe_amount"]),
                "outcome_preassigned": outcome,
            }
        )
    return records
