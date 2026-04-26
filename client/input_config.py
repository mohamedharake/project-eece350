"""
client/input_config.py

Key-binding configuration for snake movement.
"""

from __future__ import annotations

from typing import Final

import pygame

# Default movement bindings for Phase F.
# Kept as plain dict for easy future customization.
KEY_TO_DIRECTION_ARROWS: Final[dict[int, str]] = {
    pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_LEFT: "LEFT",
    pygame.K_RIGHT: "RIGHT",
}

KEY_TO_DIRECTION_WASD: Final[dict[int, str]] = {
    pygame.K_w: "UP",
    pygame.K_s: "DOWN",
    pygame.K_a: "LEFT",
    pygame.K_d: "RIGHT",
}
# I use this function to keymap for controls.


def keymap_for_controls(control_scheme: str) -> dict[int, str]:
    """Return pygame key code → direction string for WASD or arrow keys based on ``control_scheme``."""
    return KEY_TO_DIRECTION_WASD if str(control_scheme).upper() == "WASD" else KEY_TO_DIRECTION_ARROWS

