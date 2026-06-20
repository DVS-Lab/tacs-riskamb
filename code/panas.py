"""Standard 20-item PANAS questionnaire and subscale scoring."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import pygame

from stimuli import StimulusRenderer


# Standard PANAS ordering, with conventional positive/negative membership.
PANAS_ITEMS = [
    ("interested", "positive"), ("distressed", "negative"),
    ("excited", "positive"), ("upset", "negative"),
    ("strong", "positive"), ("guilty", "negative"),
    ("scared", "negative"), ("hostile", "negative"),
    ("enthusiastic", "positive"), ("proud", "positive"),
    ("irritable", "negative"), ("alert", "positive"),
    ("ashamed", "negative"), ("inspired", "positive"),
    ("nervous", "negative"), ("determined", "positive"),
    ("attentive", "positive"), ("jittery", "negative"),
    ("active", "positive"), ("afraid", "negative"),
]


def score_panas(responses: Mapping[str, int]) -> Dict[str, int]:
    """Sum 10 positive and 10 negative responses (each range 10–50)."""
    return {
        "positive_affect_total": sum(int(responses[item]) for item, scale in PANAS_ITEMS if scale == "positive"),
        "negative_affect_total": sum(int(responses[item]) for item, scale in PANAS_ITEMS if scale == "negative"),
    }


def administer_panas(renderer: StimulusRenderer, auto_respond: bool = False) -> Optional[Dict[str, Any]]:
    """Collect PANAS ratings for how the participant feels right now."""
    responses: Dict[str, int] = {}
    clock = pygame.time.Clock()
    for index, (item, _) in enumerate(PANAS_ITEMS, start=1):
        if auto_respond:
            rating = 3
        else:
            rating = 3
            confirmed = False
            while not confirmed:
                renderer.clear()
                renderer.text("How do you feel right now?", (renderer.width // 2, int(renderer.height * 0.20)), renderer.font_large)
                renderer.text(item.upper(), (renderer.width // 2, int(renderer.height * 0.45)), renderer.font_large, renderer.highlight)
                renderer.text(f"{rating}", (renderer.width // 2, int(renderer.height * 0.63)), renderer.font_large)
                renderer.text("1 very slightly / not at all     5 extremely", (renderer.width // 2, int(renderer.height * 0.78)), renderer.font_small)
                renderer.text(f"Item {index} of {len(PANAS_ITEMS)}     LEFT/RIGHT adjust, ENTER confirm", (renderer.width // 2, int(renderer.height * 0.90)), renderer.font_small)
                pygame.display.flip()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        return None
                    if event.type == pygame.KEYDOWN:
                        if pygame.K_1 <= event.key <= pygame.K_5:
                            rating = event.key - pygame.K_0
                            confirmed = True
                        elif event.key == pygame.K_LEFT:
                            rating = max(1, rating - 1)
                        elif event.key == pygame.K_RIGHT:
                            rating = min(5, rating + 1)
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            confirmed = True
                clock.tick(60)
        responses[item] = rating
    result: Dict[str, Any] = {"instruction": "right_now", "responses": responses}
    result.update(score_panas(responses))
    return result
