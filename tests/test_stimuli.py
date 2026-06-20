import pygame

from config import load_config
from stimuli import StimulusRenderer


def _trial(info, probability):
    return {
        "information_condition": info,
        "cue_shape": "circle",
        "cue_color_rgb": [66, 135, 245],
        "p_gain_actual": probability,
        "gain_amount": 5.25,
        "loss_amount": -1.75,
        "gamble_side": "left",
        "safe_side": "right",
    }


def test_hidden_probability_draws_no_text_or_informative_wedge():
    pygame.init()
    screen = pygame.display.set_mode((960, 600))
    audit = StimulusRenderer(screen, load_config()).draw_choice(_trial("hidden_probability", 0.25))
    assert audit == {"probability_text_drawn": False, "informative_wedge_drawn": False}
    pygame.quit()


def test_visible_probability_draws_correct_disclosure_elements():
    pygame.init()
    screen = pygame.display.set_mode((960, 600))
    audit = StimulusRenderer(screen, load_config()).draw_choice(_trial("risk", 0.50))
    assert audit == {"probability_text_drawn": True, "informative_wedge_drawn": True}
    pygame.quit()

