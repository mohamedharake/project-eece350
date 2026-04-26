"""
client/render.py

Pure rendering helpers for Pygame.
"""

from __future__ import annotations

from typing import Any

import pygame

from client.ui_theme import (
    ACCENT,
    BG_PANEL,
    BG_PANEL_ALT,
    BG_ROOT,
    BORDER,
    BORDER_ACCENT,
    BRAND_MAGENTA,
    OVERLAY_SCRIM,
    TEXT,
    TEXT_MUTED,
    blit_game_brand,
    fill_screen_background,
    load_fonts,
)
from shared.constants import CELL_SIZE_PX, STARTING_HEALTH

COLOR_BG = BG_ROOT
COLOR_GRID = (52, 44, 88)
COLOR_GRID_MAJOR = (92, 72, 148)
COLOR_OBSTACLE = (182, 108, 255)
COLOR_OBSTACLE_BORDER = (235, 205, 255)
COLOR_PIE_NORMAL = (238, 242, 248)
COLOR_PIE_GOLDEN = (250, 204, 75)
COLOR_PIE_POISON = (192, 80, 220)
COLOR_PIE_SPEED = (255, 120, 220)
COLOR_PIE_SHIELD = (96, 170, 255)
COLOR_TEXT = TEXT
COLOR_SNAKE_A = (56, 226, 255)
COLOR_SNAKE_B = (167, 243, 125)
COLOR_CHAT_BG = BG_PANEL
COLOR_CHAT_TEXT = (218, 224, 240)
COLOR_CHAT_INPUT = ACCENT
CHAT_PAD = 10
CHAT_MAX_LINES = 6

_PLAYER_COLORS: dict[str, tuple[int, int, int]] = {}
_PLAYER_ACCENT_FILL: tuple[int, int, int] = (72, 232, 255)
_PLAYER_ALT_FILL: tuple[int, int, int] = (110, 230, 140)
# I use this function to window size from state.


def window_size_from_state(state_payload: dict[str, Any] | None) -> tuple[int, int]:
    """Compute (width, height) in pixels from board dimensions plus fixed HUD height."""
    board = (state_payload or {}).get("board", {})
    board_w = int(board.get("width", 40))
    board_h = int(board.get("height", 30))
    hud_height = 92
    return board_w * CELL_SIZE_PX, board_h * CELL_SIZE_PX + hud_height
# I use this function to player bar colors.


def _player_bar_colors(username: str, idx: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Stable fill and background colors for a player's HUD health bar (cached per name)."""
    if username not in _PLAYER_COLORS:
        base = _PLAYER_ACCENT_FILL if idx == 0 else _PLAYER_ALT_FILL
        _PLAYER_COLORS[username] = base
    fill = _PLAYER_COLORS[username]
    bg = (28, 34, 52)
    return fill, bg
# I use this function to draw grid.


def _draw_grid(surface: pygame.Surface, board_w: int, board_h: int) -> None:
    """Fill the play area and draw a light grid with major lines every five cells."""
    play_height = board_h * CELL_SIZE_PX
    surface.fill(COLOR_BG)
    pw = board_w * CELL_SIZE_PX
    for x in range(0, pw, CELL_SIZE_PX):
        line_c = COLOR_GRID_MAJOR if x % (CELL_SIZE_PX * 5) == 0 else COLOR_GRID
        pygame.draw.line(surface, line_c, (x, 0), (x, play_height), 1)
    for y in range(0, play_height, CELL_SIZE_PX):
        line_c = COLOR_GRID_MAJOR if y % (CELL_SIZE_PX * 5) == 0 else COLOR_GRID
        pygame.draw.line(surface, line_c, (0, y), (pw, y), 1)
# I use this function to health bar.


def _health_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fraction: float,
    fill: tuple[int, int, int],
    bg: tuple[int, int, int],
) -> None:
    """Draw a rounded bar background and a partial fill proportional to ``fraction``."""
    pygame.draw.rect(surface, bg, rect, border_radius=5)
    frac = max(0.0, min(1.0, fraction))
    if frac <= 0:
        return
    inner = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.width - 4) * frac), rect.height - 4)
    pygame.draw.rect(surface, fill, inner, border_radius=4)
# I use this function to draw hud bar.


def _draw_hud_bar(
    surface: pygame.Surface,
    *,
    width: int,
    play_height: int,
    time_left: Any,
    players: list[Any],
    health: dict[str, Any],
    body: pygame.font.Font,
    tiny: pygame.font.Font,
    my_username: str,
    is_spectator: bool,
    hud_esc_hint_leaves_match: bool,
    control_scheme: str,
) -> None:
    """Draw timer pill, per-player health bars, and footnote controls or spectator hint."""
    hud_h = max(92, surface.get_height() - play_height)
    hud_rect = pygame.Rect(0, play_height, width, hud_h)

    hud_bg = pygame.Surface((hud_rect.width, hud_rect.height), pygame.SRCALPHA)
    hud_bg.fill((24, 16, 44, 252))
    surface.blit(hud_bg, hud_rect.topleft)

    pygame.draw.rect(surface, BRAND_MAGENTA, (0, play_height, width, 2))

    pill = pygame.Rect(14, play_height + 14, 118, 34)
    pygame.draw.rect(surface, BG_PANEL_ALT, pill, border_radius=10)
    pygame.draw.rect(surface, BORDER_ACCENT, pill, width=1, border_radius=10)
    time_txt = body.render(f"{time_left}s", True, ACCENT)
    surface.blit(time_txt, (pill.centerx - time_txt.get_width() // 2, pill.centery - time_txt.get_height() // 2))

    lbl = tiny.render("TIME LEFT", True, TEXT_MUTED)
    surface.blit(lbl, (pill.x + pill.width + 14, play_height + 16))

    vals = []
    for p in players:
        try:
            vals.append(int(health.get(p, 0)))
        except (TypeError, ValueError):
            vals.append(0)
    mx = max([STARTING_HEALTH] + vals) if vals else STARTING_HEALTH

    bx_start = pill.right + 96
    avail = max(120, width - bx_start - 16)
    n_players = max(len(players), 1)
    slot_w = avail // n_players
    bar_w = min(200, max(64, slot_w - 88))

    bx = bx_start
    for idx, player in enumerate(players):
        hp = int(health.get(player, 0))
        frac = hp / mx if mx else 0.0
        fill_c, bg_c = _player_bar_colors(str(player), idx)
        who = tiny.render(str(player), True, TEXT)
        YOU = ""
        if player == my_username:
            YOU = tiny.render("(you)", True, ACCENT)
        surface.blit(who, (bx, play_height + 12))
        if YOU:
            surface.blit(YOU, (bx + who.get_width() + 6, play_height + 12))

        hp_lbl = tiny.render(f"{hp} HP", True, TEXT_MUTED)
        bar_rect = pygame.Rect(bx, play_height + 34, bar_w, 14)
        _health_bar(surface, bar_rect, frac, fill_c, bg_c)
        hp_x = min(bx + bar_w + 8, bx + slot_w - hp_lbl.get_width())
        surface.blit(hp_lbl, (hp_x, play_height + 32))

        bx += slot_w

    hint_y = play_height + hud_h - 28
    if is_spectator:
        controls_line = "Spectating · arrows disabled · ESC returns to lobby" if hud_esc_hint_leaves_match else "Spectating · ESC exits"
    else:
        controls_name = "WASD" if str(control_scheme).upper() == "WASD" else "Arrows"
        controls_line = (
            f"{controls_name} move · Enter chat · ESC leaves match"
            if hud_esc_hint_leaves_match
            else f"{controls_name} move · Enter chat · ESC exits"
        )
    controls = tiny.render(controls_line, True, TEXT_MUTED)
    surface.blit(controls, (14, hint_y))
# I use this function to cell rect.


def _cell_rect(x: int, y: int) -> pygame.Rect:
    """Pixel rectangle for grid cell (x, y) with a small inner padding."""
    pad = 2
    return pygame.Rect(
        x * CELL_SIZE_PX + pad,
        y * CELL_SIZE_PX + pad,
        CELL_SIZE_PX - (2 * pad),
        CELL_SIZE_PX - (2 * pad),
    )
# I use this function to draw state.


def draw_state(
    surface: pygame.Surface,
    state_payload: dict[str, Any] | None,
    *,
    my_username: str,
    game_over_payload: dict[str, Any] | None,
    chat_messages: list[dict[str, Any]] | None = None,
    chat_input: str | None = None,
    chat_active: bool = False,
    is_spectator: bool = False,
    show_game_over_overlay: bool = True,
    hud_esc_hint_leaves_match: bool = False,
    control_scheme: str = "ARROWS",
) -> None:
    """Paint the full frame: board, entities, HUD, optional chat, optional game-over dimmer."""
    width, height = surface.get_size()
    if not state_payload:
        surface.fill(COLOR_BG)
        return

    board = state_payload.get("board", {})
    board_w = int(board.get("width", 40))
    board_h = int(board.get("height", 30))
    play_height = board_h * CELL_SIZE_PX
    _PLAYER_COLORS.clear()
    _draw_grid(surface, board_w, board_h)

    for obstacle in state_payload.get("obstacles", []):
        x = int(obstacle.get("x", 0))
        y = int(obstacle.get("y", 0))
        obstacle_rect = _cell_rect(x, y)
        pygame.draw.rect(surface, COLOR_OBSTACLE, obstacle_rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_OBSTACLE_BORDER, obstacle_rect, width=1, border_radius=5)

    for pie in state_payload.get("pies", []):
        x = int(pie.get("x", 0))
        y = int(pie.get("y", 0))
        kind = str(pie.get("kind", "normal")).lower()
        if kind == "golden":
            color = COLOR_PIE_GOLDEN
        elif kind == "poison":
            color = COLOR_PIE_POISON
        elif kind == "speed":
            color = COLOR_PIE_SPEED
        elif kind == "shield":
            color = COLOR_PIE_SHIELD
        else:
            color = COLOR_PIE_NORMAL
        pygame.draw.ellipse(surface, color, _cell_rect(x, y))

    for snake in state_payload.get("snakes", []):
        owner = snake.get("owner", "")
        body = snake.get("body", [])
        style = str(snake.get("style", "")).lower()
        color_map: dict[str, tuple[int, int, int]] = {
            "default_a": COLOR_SNAKE_A,
            "default_b": COLOR_SNAKE_B,
            "cyan": (56, 226, 255),
            "lime": (167, 243, 125),
            "rose": (244, 114, 182),
            "amber": (250, 204, 75),
            "violet": (196, 181, 253),
        }
        color = color_map.get(style, COLOR_SNAKE_A)
        if owner == my_username:
            color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        for idx, segment in enumerate(body):
            x = int(segment.get("x", 0))
            y = int(segment.get("y", 0))
            rect = _cell_rect(x, y)
            pygame.draw.rect(surface, color, rect, border_radius=5)
            if idx == 0:
                pygame.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=5)

    _, body_font, small_font, tiny_font = load_fonts()
    health = state_payload.get("health_by_player", {})
    players = state_payload.get("players", [])
    time_left = state_payload.get("time_left_s", 0)
    _draw_hud_bar(
        surface,
        width=width,
        play_height=play_height,
        time_left=time_left,
        players=players,
        health=health,
        body=body_font,
        tiny=tiny_font,
        my_username=my_username,
        is_spectator=is_spectator,
        hud_esc_hint_leaves_match=hud_esc_hint_leaves_match,
        control_scheme=control_scheme,
    )

    chat_messages = chat_messages or []
    recent = chat_messages[-CHAT_MAX_LINES:]
    if recent or chat_active or chat_input:
        panel_width = min(width // 3 + 52, width // 2)
        lines_count = len(recent) + (1 if chat_active or chat_input else 0)
        inner_h = max(30, lines_count * 19 + CHAT_PAD * 2)
        panel_height = inner_h + 34
        panel_rect = pygame.Rect(width - panel_width - 16, 14, panel_width, panel_height)

        shadow = panel_rect.copy()
        shadow.y += 3
        pygame.draw.rect(surface, (4, 6, 14), shadow, border_radius=12)

        pygame.draw.rect(surface, COLOR_CHAT_BG, panel_rect, border_radius=12)
        pygame.draw.rect(surface, BORDER_ACCENT, panel_rect, width=1, border_radius=12)
        accent_strip = pygame.Rect(panel_rect.x + 12, panel_rect.y + 8, panel_rect.width - 24, 3)
        pygame.draw.rect(surface, BORDER_ACCENT, accent_strip, border_radius=2)

        hdr = small_font.render("CHAT", True, ACCENT)
        surface.blit(hdr, (panel_rect.x + CHAT_PAD + 6, panel_rect.y + 12))
        inner = pygame.Rect(
            panel_rect.x + CHAT_PAD,
            panel_rect.y + 38,
            panel_rect.width - CHAT_PAD * 2,
            inner_h,
        )
        pygame.draw.rect(surface, BG_PANEL_ALT, inner, border_radius=8)
        pygame.draw.rect(surface, BORDER, inner, width=1, border_radius=8)
        y = inner.y + CHAT_PAD // 2 + 2
        for msg in recent:
            line_txt = f"{msg.get('from', '?')}: {msg.get('text', '')}"
            line_surf = small_font.render(line_txt[:76], True, COLOR_CHAT_TEXT)
            surface.blit(line_surf, (inner.x + CHAT_PAD, y))
            y += 19
            if y > inner.bottom - 16:
                break
        if chat_active or chat_input:
            prefix = "> " + (chat_input or "")
            input_surf = small_font.render(prefix[:76], True, COLOR_CHAT_INPUT)
            surface.blit(input_surf, (inner.x + CHAT_PAD, min(y, inner.bottom - 22)))

    if game_over_payload and show_game_over_overlay:
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(OVERLAY_SCRIM)
        surface.blit(overlay, (0, 0))
        winner = game_over_payload.get("winner_username")
        reason = game_over_payload.get("reason", "unknown")
        title_f, _, small_f, tiny_f = load_fonts()
        text = f"Victory — {winner}" if winner else "Draw"
        text_surf = title_f.render(text, True, ACCENT)
        reason_surf = small_f.render(f"Reason: {reason}", True, TEXT_MUTED)
        close_surf = tiny_f.render("Close window or press ESC to continue.", True, TEXT)
        surface.blit(text_surf, (max(20, (width - text_surf.get_width()) // 2), max(24, height // 2 - 52)))
        surface.blit(reason_surf, (max(20, (width - reason_surf.get_width()) // 2), max(24, height // 2 - 8)))
        surface.blit(close_surf, (max(20, (width - close_surf.get_width()) // 2), max(24, height // 2 + 22)))
# I use this function to draw waiting for state.


def draw_waiting_for_state(surface: pygame.Surface, message: str | None = None) -> None:
    """Branded full-window placeholder with optional status line until state arrives."""
    fill_screen_background(surface)
    msg = message or "Syncing with server…"
    title_f, body_f, _, tiny_f = load_fonts()
    tw, th = surface.get_size()
    y_brand = th // 2 - 56
    blit_game_brand(surface, title_f, cx=tw // 2, top=y_brand)
    sub = body_f.render(msg, True, TEXT_MUTED)
    hint = tiny_f.render("Hang tight — my arena match is loading.", True, TEXT_MUTED)
    surface.blit(sub, ((tw - sub.get_width()) // 2, th // 2 - 6))
    surface.blit(hint, ((tw - hint.get_width()) // 2, th // 2 + 28))
