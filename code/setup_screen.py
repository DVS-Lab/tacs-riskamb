"""Experimenter-only graphical setup when CLI identifiers are omitted."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import pygame


def experimenter_setup(screen: pygame.Surface, defaults: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Collect identifiers and laboratory settings before participant handoff."""
    width, height = screen.get_size()
    font = pygame.font.Font(None, max(26, int(min(width, height) * 0.042)))
    small = pygame.font.Font(None, max(20, int(min(width, height) * 0.030)))
    fields = ["subject", "session", "run"]
    values = {
        "subject": str(defaults.get("subject") or ""),
        "session": str(defaults.get("session") or "1"),
        "run": str(defaults.get("run") or "1"),
        "display_index": int(defaults.get("display_index", 0)),
        "fullscreen": bool(defaults.get("fullscreen", False)),
        "trigger_mode": str(defaults.get("trigger_mode", "space")),
        "test_mode": bool(defaults.get("test_mode", False)),
    }
    active = 0
    trigger_modes = ["space", "scanner", "lsl"]
    clock = pygame.time.Clock()
    while True:
        screen.fill((22, 25, 33))
        title = font.render("EXPERIMENTER SETUP — not participant-facing", True, (255, 214, 87))
        screen.blit(title, title.get_rect(center=(width // 2, int(height * 0.12))))
        lines = [
            f"Subject: {values['subject']}",
            f"Session: {values['session']}",
            f"Run: {values['run']}",
        ]
        for index, line in enumerate(lines):
            color = (255, 214, 87) if index == active else (238, 240, 244)
            surface = font.render(("> " if index == active else "  ") + line, True, color)
            screen.blit(surface, (int(width * 0.22), int(height * (0.25 + index * 0.09))))
        settings = [
            f"Display index: {values['display_index']}   (D changes)",
            f"Fullscreen: {values['fullscreen']}   (F toggles)",
            f"Trigger mode: {values['trigger_mode']}   (T cycles)",
            f"Test mode: {values['test_mode']}   (M toggles)",
        ]
        for index, line in enumerate(settings):
            surface = small.render(line, True, (190, 196, 207))
            screen.blit(surface, (int(width * 0.22), int(height * (0.57 + index * 0.065))))
        footer = small.render("TAB selects field • ENTER starts • ESC cancels", True, (238, 240, 244))
        screen.blit(footer, footer.get_rect(center=(width // 2, int(height * 0.91))))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    active = (active + 1) % len(fields)
                elif event.key == pygame.K_BACKSPACE:
                    values[fields[active]] = values[fields[active]][:-1]
                elif event.key == pygame.K_d:
                    values["display_index"] = (values["display_index"] + 1) % max(1, pygame.display.get_num_displays())
                elif event.key == pygame.K_f:
                    values["fullscreen"] = not values["fullscreen"]
                elif event.key == pygame.K_t:
                    current = trigger_modes.index(values["trigger_mode"])
                    values["trigger_mode"] = trigger_modes[(current + 1) % len(trigger_modes)]
                elif event.key == pygame.K_m:
                    values["test_mode"] = not values["test_mode"]
                elif event.key == pygame.K_RETURN:
                    if values["subject"] and values["session"] and values["run"].isdigit():
                        return values
                elif event.unicode.isalnum() or event.unicode in "-_":
                    values[fields[active]] += event.unicode
        clock.tick(60)
