"""
client/screens/game_over_screen.py

Post-match summary: winner, scores, return to lobby or exit.
"""

from __future__ import annotations

from typing import Any, Literal

import pygame

from client.ui_theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESS,
    BG_PANEL,
    BORDER,
    BORDER_ACCENT,
    BRAND_GOLD_PI,
    BRAND_MAGENTA,
    DANGER,
    DANGER_HOVER,
    OVERLAY_SCRIM,
    SHADOW,
    TEXT,
    TEXT_MUTED,
    draw_card_shadow,
    draw_panel,
    draw_rounded_button,
    fill_screen_background,
)

GameOverAction = Literal["lobby", "quit", "none"]
# I use this function to layout buttons.


def _layout_buttons(surface: pygame.Surface) -> tuple[pygame.Rect, pygame.Rect]:
    """Return centered side-by-side rects for Return to lobby and Exit game."""
    w, h = surface.get_size()
    gap = 18
    bw, bh = 218, 52
    total = bw * 2 + gap
    y = h // 2 + 72
    x0 = (w - total) // 2
    return pygame.Rect(x0, y, bw, bh), pygame.Rect(x0 + bw + gap, y, bw, bh)
# I use this function to draw game over.


def draw_game_over(
    surface: pygame.Surface,
    *,
    game_over_payload: dict[str, Any],
    title_font: pygame.font.Font,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    tiny_font: pygame.font.Font,
    mouse_pos: tuple[int, int] | None = None,
) -> None:
    """Draw the match summary card: winner or draw, scores, reason, and two action buttons."""
    fill_screen_background(surface)
    mouse_down = bool(pygame.mouse.get_pressed()[0])
    scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    scrim.fill(OVERLAY_SCRIM)
    surface.blit(scrim, (0, 0))

    winner = game_over_payload.get("winner_username")
    reason = str(game_over_payload.get("reason", ""))
    health = game_over_payload.get("health_by_player", {})
    scores = game_over_payload.get("score_by_player", {})

    w, h = surface.get_size()
    panel = pygame.Rect((w - 640) // 2, max(56, h // 2 - 190), 640, 324)
    draw_card_shadow(surface, panel)
    draw_panel(surface, panel, bg=BG_PANEL, border_color=BORDER_ACCENT, radius=20, accent_top=True)

    trophy = tiny_font.render("MATCH COMPLETE", True, BRAND_GOLD_PI)
    surface.blit(trophy, ((w - trophy.get_width()) // 2, panel.y + 22))

    if winner:
        headline = winner
        head_surf = title_font.render(headline, True, BRAND_MAGENTA)
        surface.blit(head_surf, ((w - head_surf.get_width()) // 2, panel.y + 52))
        subt = font.render("claims the arena", True, TEXT_MUTED)
        surface.blit(subt, ((w - subt.get_width()) // 2, panel.y + 98))
    else:
        head_surf = title_font.render("DRAW", True, ACCENT)
        surface.blit(head_surf, ((w - head_surf.get_width()) // 2, panel.y + 68))

    y_detail = panel.y + 138
    if isinstance(scores, dict) and scores:
        order = sorted(scores.keys())
        parts = [f"{k}  ·  {scores[k]} pts" for k in order]
        score_line = "   ·   ".join(parts)
        sc = small_font.render(score_line[:110], True, TEXT)
        surface.blit(sc, ((w - sc.get_width()) // 2, y_detail))

    if isinstance(health, dict) and health:
        parts_h = [f"{k}: {health[k]} HP" for k in sorted(health.keys())]
        hl = small_font.render("   ".join(parts_h), True, TEXT_MUTED)
        surface.blit(hl, ((w - hl.get_width()) // 2, y_detail + 30))

    rs = small_font.render(f"Reason: {reason}", True, TEXT_MUTED)
    surface.blit(rs, ((w - rs.get_width()) // 2, y_detail + (58 if health else 32)))

    div_y = panel.bottom - 100
    pygame.draw.line(surface, BORDER, (panel.x + 40, div_y), (panel.right - 40, div_y), 1)

    lob_r, ex_r = _layout_buttons(surface)
    pygame.draw.rect(surface, SHADOW, lob_r.move(0, 3), border_radius=12)
    pygame.draw.rect(surface, SHADOW, ex_r.move(0, 3), border_radius=12)
    draw_rounded_button(
        surface,
        lob_r,
        "Return to lobby",
        font,
        bg=ACCENT,
        bg_hover=ACCENT_HOVER,
        bg_pressed=ACCENT_PRESS,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
        border_color=BORDER_ACCENT,
        glow_accent=True,
    )
    draw_rounded_button(
        surface,
        ex_r,
        "Exit game",
        font,
        bg=DANGER,
        bg_hover=DANGER_HOVER,
        bg_pressed=DANGER,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
        border_color=BORDER,
    )
# I use this function to handle game over event.


def handle_game_over_event(event: pygame.event.Event, surface: pygame.Surface) -> GameOverAction:
    """On left click, return lobby/quit if a button was hit; otherwise ``none``."""
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return "none"
    lob_r, ex_r = _layout_buttons(surface)
    if lob_r.collidepoint(event.pos):
        return "lobby"
    if ex_r.collidepoint(event.pos):
        return "quit"
    return "none"
