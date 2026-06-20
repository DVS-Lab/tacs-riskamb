"""Resolution-proportional, programmatic Pygame stimuli."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import pygame


def money(amount: float) -> str:
    sign = "+" if amount > 0 else "−" if amount < 0 else ""
    return f"{sign}${abs(amount):.2f}"


class StimulusRenderer:
    """Render choice and feedback screens without raster lottery assets."""

    def __init__(self, screen: pygame.Surface, config: Mapping[str, Any]) -> None:
        self.screen = screen
        self.config = config
        self.width, self.height = screen.get_size()
        display = config["display"]
        self.bg = tuple(display["background"])
        self.fg = tuple(display["foreground"])
        self.gain = tuple(display["gain_color"])
        self.loss = tuple(display["loss_color"])
        self.mask = tuple(display["mask_color"])
        self.highlight = tuple(display["highlight_color"])
        base = min(self.width, self.height)
        self.font_large = pygame.font.Font(None, max(34, int(base * 0.075)))
        self.font_medium = pygame.font.Font(None, max(26, int(base * 0.045)))
        self.font_small = pygame.font.Font(None, max(20, int(base * 0.030)))
        self.option_size = int(base * 0.38)
        self.centers = {
            "left": (int(self.width * 0.28), int(self.height * 0.50)),
            "right": (int(self.width * 0.72), int(self.height * 0.50)),
        }

    def clear(self) -> None:
        self.screen.fill(self.bg)

    def text(
        self, value: str, center: Tuple[int, int], font: Optional[pygame.font.Font] = None,
        color: Optional[Tuple[int, int, int]] = None,
    ) -> pygame.Rect:
        surface = (font or self.font_medium).render(value, True, color or self.fg)
        rectangle = surface.get_rect(center=center)
        self.screen.blit(surface, rectangle)
        return rectangle

    def draw_fixation(self) -> None:
        self.clear()
        size = int(min(self.width, self.height) * 0.025)
        center = (self.width // 2, self.height // 2)
        pygame.draw.line(self.screen, self.fg, (center[0] - size, center[1]), (center[0] + size, center[1]), 4)
        pygame.draw.line(self.screen, self.fg, (center[0], center[1] - size), (center[0], center[1] + size), 4)

    def _polygon(self, center: Tuple[int, int], radius: int, sides: int, rotation: float = -math.pi / 2) -> Sequence[Tuple[int, int]]:
        return [
            (
                int(center[0] + radius * math.cos(rotation + 2 * math.pi * i / sides)),
                int(center[1] + radius * math.sin(rotation + 2 * math.pi * i / sides)),
            )
            for i in range(sides)
        ]

    def draw_cue(self, center: Tuple[int, int], trial: Mapping[str, Any]) -> None:
        color = tuple(trial.get("cue_color_rgb", [66, 135, 245]))
        radius = int(self.option_size * 0.53)
        shape = trial["cue_shape"]
        if shape == "circle":
            pygame.draw.circle(self.screen, color, center, radius, 8)
        elif shape == "star":
            points = []
            for i in range(10):
                local_radius = radius if i % 2 == 0 else int(radius * 0.48)
                angle = -math.pi / 2 + i * math.pi / 5
                points.append((int(center[0] + local_radius * math.cos(angle)), int(center[1] + local_radius * math.sin(angle))))
            pygame.draw.polygon(self.screen, color, points, 8)
        else:
            sides = {"triangle": 3, "square": 4, "diamond": 4, "pentagon": 5, "hexagon": 6, "octagon": 8}.get(shape, 6)
            rotation = math.pi / 4 if shape == "diamond" else -math.pi / 2
            pygame.draw.polygon(self.screen, color, self._polygon(center, radius, sides, rotation), 8)

    def _visible_pie(self, center: Tuple[int, int], radius: int, p_gain: float) -> None:
        pygame.draw.circle(self.screen, self.loss, center, radius)
        # Gain wedge begins at 12 o'clock and is exactly proportional to p_gain.
        steps = max(3, int(72 * p_gain))
        points = [center]
        for index in range(steps + 1):
            angle = -math.pi / 2 + (2 * math.pi * p_gain * index / steps)
            points.append((int(center[0] + radius * math.cos(angle)), int(center[1] + radius * math.sin(angle))))
        pygame.draw.polygon(self.screen, self.gain, points)
        pygame.draw.circle(self.screen, self.fg, center, radius, 3)

    def draw_gamble(self, trial: Mapping[str, Any], center: Tuple[int, int]) -> Dict[str, bool]:
        """Draw one gamble and return a testable probability-disclosure audit."""
        self.draw_cue(center, trial)
        pie_center = (center[0], center[1] - int(self.option_size * 0.06))
        pie_radius = int(self.option_size * 0.20)
        hidden = trial["information_condition"] == "hidden_probability"
        audit = {"probability_text_drawn": False, "informative_wedge_drawn": False}
        if hidden:
            # Identical full mask at every hidden probability: no wedge geometry survives.
            pygame.draw.circle(self.screen, self.mask, pie_center, pie_radius)
            pygame.draw.circle(self.screen, self.fg, pie_center, pie_radius, 3)
            self.text("?", pie_center, self.font_large)
        else:
            self._visible_pie(pie_center, pie_radius, float(trial["p_gain_actual"]))
            label_y = pie_center[1] + pie_radius + int(self.option_size * 0.09)
            self.text(f"{float(trial['p_gain_actual']) * 100:.0f}% chance of gain", (center[0], label_y), self.font_small)
            audit = {"probability_text_drawn": True, "informative_wedge_drawn": True}
        amount_y = center[1] + int(self.option_size * 0.32)
        self.text(money(float(trial["gain_amount"])), (center[0] - int(self.option_size * 0.16), amount_y), self.font_medium, self.gain)
        self.text(money(float(trial["loss_amount"])), (center[0] + int(self.option_size * 0.16), amount_y), self.font_medium, self.loss)
        return audit

    def draw_safe(self, center: Tuple[int, int]) -> None:
        rectangle = pygame.Rect(0, 0, self.option_size, int(self.option_size * 0.62))
        rectangle.center = center
        pygame.draw.rect(self.screen, (56, 62, 75), rectangle, border_radius=18)
        pygame.draw.rect(self.screen, self.fg, rectangle, 4, border_radius=18)
        self.text("GUARANTEED $0", center, self.font_medium)

    def draw_choice(self, trial: Mapping[str, Any], selected: Optional[str] = None) -> Dict[str, bool]:
        self.clear()
        gamble_center = self.centers[str(trial["gamble_side"])]
        safe_center = self.centers[str(trial["safe_side"])]
        audit = self.draw_gamble(trial, gamble_center)
        self.draw_safe(safe_center)
        if selected in ("left", "right"):
            rectangle = pygame.Rect(0, 0, int(self.option_size * 1.25), int(self.option_size * 1.25))
            rectangle.center = self.centers[selected]
            pygame.draw.rect(self.screen, self.highlight, rectangle, 7, border_radius=25)
        key_y = int(self.height * 0.88)
        self.text("F", (self.centers["left"][0], key_y), self.font_small)
        self.text("J", (self.centers["right"][0], key_y), self.font_small)
        return audit

    def draw_feedback(self, trial: Mapping[str, Any], choice: str, responded: bool) -> None:
        self.clear()
        outcome = trial["outcome_preassigned"]
        amount = float(trial["gain_amount"] if outcome == "gain" else trial["loss_amount"])
        color = self.gain if outcome == "gain" else self.loss
        if not responded:
            self.text("Too slow.", (self.width // 2, int(self.height * 0.34)), self.font_large, self.highlight)
        elif choice == "safe":
            self.text("You chose $0.", (self.width // 2, int(self.height * 0.34)), self.font_large)
        else:
            self.text(f"Lottery outcome: {money(amount)}", (self.width // 2, int(self.height * 0.34)), self.font_large, color)
        if (not responded or choice == "safe") and self.config["task"].get("counterfactual_feedback", True):
            self.text(f"Lottery outcome: {money(amount)}", (self.width // 2, int(self.height * 0.57)), self.font_medium, color)

    def draw_belief_probe(self, trial: Mapping[str, Any], estimate: int, confidence: int, stage: str) -> None:
        self.clear()
        self.draw_cue((self.width // 2, int(self.height * 0.26)), trial)
        if stage == "probability":
            self.text("Estimated chance of a gain", (self.width // 2, int(self.height * 0.52)), self.font_medium)
            self.text(f"{estimate}%", (self.width // 2, int(self.height * 0.64)), self.font_large, self.highlight)
            self.text("LEFT / RIGHT adjust     ENTER confirm", (self.width // 2, int(self.height * 0.82)), self.font_small)
        else:
            self.text("How confident are you?", (self.width // 2, int(self.height * 0.52)), self.font_medium)
            self.text(f"{confidence} / 9", (self.width // 2, int(self.height * 0.64)), self.font_large, self.highlight)
            self.text("LEFT / RIGHT adjust     ENTER confirm", (self.width // 2, int(self.height * 0.82)), self.font_small)
