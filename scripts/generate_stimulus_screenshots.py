#!/usr/bin/env python3
"""Generate representative QA screenshots using the production renderer."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import pygame  # noqa: E402

from config import load_config  # noqa: E402
from stimuli import StimulusRenderer  # noqa: E402


def trial(skew: str, information: str, outcome: str = "gain", side: str = "left") -> dict:
    config = load_config()
    gamble = config["gambles"][skew]
    cues = {
        "symmetric": ("cue_A", "blue", [66, 135, 245], "circle"),
        "positive_skew": ("cue_B", "orange", [242, 143, 45], "octagon"),
    }
    cue_id, color_name, color, shape = cues[skew]
    return {
        "skew_condition": skew, "information_condition": information,
        "cue_id": cue_id, "cue_color": color_name, "cue_color_rgb": color,
        "cue_shape": shape, "gamble_side": side,
        "safe_side": "right" if side == "left" else "left",
        "p_gain_actual": gamble["p_gain"], "gain_amount": gamble["gain_amount"],
        "loss_amount": gamble["loss_amount"], "outcome_preassigned": outcome,
    }


def save(screen: pygame.Surface, output: Path, name: str) -> None:
    pygame.display.flip()
    pygame.image.save(screen, str(output / f"{name}.png"))


def main() -> int:
    pygame.init()
    config = load_config()
    config["display"].update({"width": 1280, "height": 800, "fullscreen": False})
    screen = pygame.display.set_mode((1280, 800))
    renderer = StimulusRenderer(screen, config)
    output = ROOT / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)

    examples = [
        ("symmetric_visible", trial("symmetric", "risk")),
        ("symmetric_hidden", trial("symmetric", "hidden_probability")),
        ("positive_skew_visible", trial("positive_skew", "risk")),
        ("positive_skew_hidden", trial("positive_skew", "hidden_probability")),
    ]
    for name, item in examples:
        renderer.draw_choice(item)
        save(screen, output, name)
    selected_gamble = trial("positive_skew", "risk", side="right")
    renderer.draw_choice(selected_gamble, selected="right")
    save(screen, output, "selected_gamble")
    renderer.draw_choice(selected_gamble, selected="left")
    save(screen, output, "selected_safe")
    for name, outcome, choice, responded in [
        ("feedback_gain", "gain", "gamble", True),
        ("feedback_loss", "loss", "gamble", True),
        ("feedback_miss", "loss", "miss", False),
    ]:
        item = trial("positive_skew", "hidden_probability", outcome=outcome)
        renderer.draw_feedback(item, choice, responded)
        save(screen, output, name)
    renderer.draw_belief_probe(trial("symmetric", "risk"), 50, 5, "probability")
    save(screen, output, "belief_estimate")
    pygame.quit()
    print(f"Wrote 10 screenshots to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

