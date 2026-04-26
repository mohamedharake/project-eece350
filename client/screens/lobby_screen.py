"""
client/screens/lobby_screen.py

Lobby: online users, challenge / spectate, incoming challenge dialog, field intel (tips).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from client.ui_theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESS,
    BG_PANEL,
    BG_PANEL_ALT,
    BORDER,
    BORDER_ACCENT,
    BRAND_GOLD_PI,
    BRAND_MAGENTA,
    BRAND_VIOLET,
    blit_game_brand_left,
    DANGER,
    DANGER_HOVER,
    OVERLAY_SCRIM,
    SHADOW,
    SUCCESS,
    SUCCESS_HOVER,
    TEXT,
    TEXT_MUTED,
    draw_card_shadow,
    draw_outline_button,
    draw_panel,
    draw_pill_label,
    draw_rounded_button,
    draw_toast,
    draw_menu_background,
    wrap_text_lines,
)


LOBBY_INTEL_LINES: tuple[tuple[tuple[int, int, int], str], ...] = (
    (ACCENT, "Chat is for matches only. Press Enter to type."),
    (BRAND_MAGENTA, "Challenge someone in the list, or Watch a live game."),
    (BRAND_VIOLET, "Arrows move my snake; mind the timer and HP bars."),
    (BRAND_GOLD_PI, "Golden pies score big; poison pies hurt."),
    (SUCCESS, "ESC in a match brings you back here."),
)


@dataclass
class LobbyScreenState:
    selected_username: str | None = None
    incoming_challenge_from: str | None = None
    toast_message: str = ""
    toast_until_ms: int = 0


@dataclass
class LobbyLayout:
    user_rows: list[tuple[pygame.Rect, dict[str, Any]]]
    play_rect: pygame.Rect
    watch_rect: pygame.Rect
    refresh_rect: pygame.Rect
    challenge_accept: pygame.Rect
    challenge_reject: pygame.Rect
    modal_rect: pygame.Rect
    intel_panel: pygame.Rect
    intel_inner: pygame.Rect
# I use this function to avatar color.


def _avatar_color(name: str) -> tuple[int, int, int]:
    """Pick a deterministic accent color from the user name for avatar circles."""
    if not name:
        return (90, 100, 130)
    h = sum(ord(c) * (i + 7) for i, c in enumerate(name[:12])) % 360
    palette = (
        (ACCENT[0], ACCENT[1], ACCENT[2]),
        (129, 140, 248),
        (244, 114, 182),
        (52, 211, 153),
        (251, 191, 36),
        (147, 197, 253),
        BRAND_VIOLET,
    )
    return palette[h % len(palette)]
# I use this function to fit text.


def _fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Ellipsize ``text`` so it fits ``max_width`` when rendered with ``font``."""
    if font.size(text)[0] <= max_width:
        return text
    base = text
    while base and font.size(base + "...")[0] > max_width:
        base = base[:-1]
    return (base + "...") if base else ""
# I use this function to layout.


def _layout(surface: pygame.Surface, user_entries: list[dict[str, Any]], my_username: str) -> LobbyLayout:
    """Compute rectangles for user rows, action buttons, challenge modal, and tips panel."""
    w, h = surface.get_size()
    margin = 32
    header_h = 96
    left_w = (w - 3 * margin) // 2

    btn_h = 46
    # Keep action buttons clear of the user pill in the header.
    btn_top = 126
    play_w = 148
    gap = 14
    play_r = pygame.Rect(margin, btn_top, play_w, btn_h)
    watch_r = pygame.Rect(play_r.right + gap, btn_top, 118, btn_h)
    refresh_r = pygame.Rect(watch_r.right + gap, btn_top, 118, btn_h)

    list_title_y = play_r.bottom + 16
    row_h = 48
    y = list_title_y + 26
    user_rows: list[tuple[pygame.Rect, dict[str, Any]]] = []
    max_rows = max(1, (h - y - margin - 56) // (row_h + 8))
    count = 0
    for item in user_entries:
        if count >= max_rows:
            break
        name = item.get("username", "")
        if name == my_username:
            continue
        r = pygame.Rect(margin, y, left_w, row_h)
        user_rows.append((r, item))
        y += row_h + 8
        count += 1

    intel_x = margin * 2 + left_w
    # Keep intel panel clearly below the header/action row.
    intel_top = max(header_h + 12, refresh_r.bottom + 14)
    intel_panel = pygame.Rect(intel_x, intel_top, w - intel_x - margin, h - intel_top - margin - 52)

    mw, mh = 460, 240
    modal = pygame.Rect((w - mw) // 2, (h - mh) // 2, mw, mh)
    aw, ah = 148, 48
    acc = pygame.Rect(modal.centerx - aw - 12, modal.bottom - ah - 28, aw, ah)
    rej = pygame.Rect(modal.centerx + 12, modal.bottom - ah - 28, aw, ah)

    intel_inner = pygame.Rect(
        intel_panel.x + 14,
        intel_panel.y + 54,
        intel_panel.width - 28,
        intel_panel.height - 72,
    )

    return LobbyLayout(
        user_rows=user_rows,
        play_rect=play_r,
        watch_rect=watch_r,
        refresh_rect=refresh_r,
        challenge_accept=acc,
        challenge_reject=rej,
        modal_rect=modal,
        intel_panel=intel_panel,
        intel_inner=intel_inner,
    )
# I use this function to draw lobby.


def draw_lobby(
    surface: pygame.Surface,
    state: LobbyScreenState,
    *,
    user_entries: list[dict[str, Any]],
    my_username: str,
    title_font: pygame.font.Font,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    tiny_font: pygame.font.Font,
    time_ms: int,
    mouse_pos: tuple[int, int] | None = None,
) -> None:
    """Render header, user list, actions, tips, optional toast, and challenge modal."""
    draw_menu_background(surface)
    mouse_down = bool(pygame.mouse.get_pressed()[0])

    layout = _layout(surface, user_entries, my_username)

    header_bg = pygame.Rect(0, 0, surface.get_width(), 92)
    hdr_surf = pygame.Surface((header_bg.width, header_bg.height), pygame.SRCALPHA)
    hdr_surf.fill((28, 18, 52, 252))
    surface.blit(hdr_surf, header_bg.topleft)
    stripe = pygame.Surface((header_bg.width, 4), pygame.SRCALPHA)
    for sx in range(0, stripe.get_width(), 3):
        pygame.draw.line(stripe, (*BRAND_MAGENTA, 120), (sx, 0), (sx + 1, 3), 1)
        pygame.draw.line(stripe, (*ACCENT, 90), (sx + 1, 0), (sx + 2, 3), 1)
    surface.blit(stripe, (0, header_bg.bottom - 5))

    brand_bottom = blit_game_brand_left(surface, title_font, left_x=32, top=18)

    pill_top = brand_bottom + 10
    pill_w = max(240, min(420, surface.get_width() - 460))
    pill = pygame.Rect(32, pill_top, pill_w, 34)
    user_label = _fit_text(font, f"User  {my_username}", pill.width - 18)
    draw_pill_label(
        surface,
        pill,
        user_label,
        font,
        bg=BG_PANEL_ALT,
        text_color=TEXT,
    )

    lobby_lbl = small_font.render("LOBBY", True, TEXT)
    lobby_y = 22
    surface.blit(lobby_lbl, (surface.get_width() - lobby_lbl.get_width() - 36, lobby_y))

    draw_rounded_button(
        surface,
        layout.play_rect,
        "Challenge",
        font,
        bg=ACCENT,
        bg_hover=ACCENT_HOVER,
        bg_pressed=ACCENT_PRESS,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
        border_color=BORDER_ACCENT,
        glow_accent=True,
    )
    draw_outline_button(
        surface,
        layout.watch_rect,
        "Watch",
        font,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
    )
    draw_outline_button(
        surface,
        layout.refresh_rect,
        "Refresh",
        font,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
    )

    list_title_y = layout.play_rect.bottom + 16
    list_title = small_font.render("ONLINE PLAYERS — tap a row to select", True, TEXT)
    surface.blit(list_title, (32, list_title_y))

    for rect, item in layout.user_rows:
        uname = str(item.get("username", ""))
        st = str(item.get("status", ""))
        selected = state.selected_username == uname

        row_shadow = rect.copy()
        row_shadow.y += 2
        pygame.draw.rect(surface, SHADOW, row_shadow, border_radius=12)

        bg = (46, 38, 82) if selected else BG_PANEL_ALT
        border_c = BORDER_ACCENT if selected else BORDER
        pygame.draw.rect(surface, bg, rect, border_radius=12)
        pygame.draw.rect(surface, border_c, rect, width=2 if selected else 1, border_radius=12)

        av_r = pygame.Rect(rect.x + 12, rect.y + 10, 28, 28)
        pygame.draw.circle(surface, _avatar_color(uname), av_r.center, 14)
        initial = (uname[:1] or "?").upper()
        ini_s = tiny_font.render(initial, True, TEXT)
        surface.blit(ini_s, (av_r.centerx - ini_s.get_width() // 2, av_r.centery - ini_s.get_height() // 2))

        name_s = font.render(uname, True, TEXT)
        surface.blit(name_s, (rect.x + 52, rect.y + 8))
        status_s = tiny_font.render(st.upper(), True, TEXT_MUTED)
        surface.blit(status_s, (rect.x + 52, rect.y + 28))

        if selected:
            sel = tiny_font.render("SELECTED", True, BRAND_GOLD_PI)
            surface.blit(sel, (rect.right - sel.get_width() - 14, rect.centery - sel.get_height() // 2))

    draw_card_shadow(surface, layout.intel_panel)
    draw_panel(surface, layout.intel_panel, bg=BG_PANEL, border_color=BORDER_ACCENT, radius=16, accent_top=True)

    hdr = small_font.render("HOW TO PLAY?", True, BRAND_GOLD_PI)
    surface.blit(hdr, (layout.intel_panel.x + 18, layout.intel_panel.y + 14))
    hint = tiny_font.render("Tips for my next arena run", True, TEXT_MUTED)
    surface.blit(hint, (layout.intel_panel.x + 18, layout.intel_panel.y + 38))

    intel_bg = pygame.Rect(layout.intel_inner)
    pygame.draw.rect(surface, (18, 14, 36), intel_bg, border_radius=12)
    pygame.draw.rect(surface, BORDER, intel_bg, width=1, border_radius=12)

    inner = layout.intel_inner
    text_left = inner.x + 36
    text_max_w = inner.width - 44
    line_skip = small_font.get_height() + 3
    block_gap = 8
    y = inner.y + 12
    done_intel = False
    for dot_color, tip in LOBBY_INTEL_LINES:
        if done_intel:
            break
        wrapped = wrap_text_lines(small_font, tip, text_max_w)
        for li, ln in enumerate(wrapped):
            if y + small_font.get_height() > inner.bottom - 8:
                done_intel = True
                break
            if li == 0:
                bullet = pygame.Rect(inner.x + 14, y + 4, 8, 8)
                pygame.draw.rect(surface, dot_color, bullet, border_radius=3)
            line_surf = small_font.render(ln, True, (220, 224, 248))
            surface.blit(line_surf, (text_left, y))
            y += line_skip
        if done_intel:
            break
        y += block_gap

    if state.toast_message and time_ms < state.toast_until_ms:
        toast_r = pygame.Rect(surface.get_width() // 2 - 240, surface.get_height() - 58, 480, 44)
        draw_toast(surface, toast_r, state.toast_message, small_font)

    if state.incoming_challenge_from:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_SCRIM)
        surface.blit(overlay, (0, 0))

        draw_card_shadow(surface, layout.modal_rect)
        draw_panel(surface, layout.modal_rect, bg=BG_PANEL, border_color=BORDER_ACCENT, radius=18, accent_top=True)
        msg = title_font.render("CHALLENGE", True, ACCENT)
        surface.blit(msg, (layout.modal_rect.centerx - msg.get_width() // 2, layout.modal_rect.y + 28))
        who = font.render(state.incoming_challenge_from, True, TEXT)
        surface.blit(who, (layout.modal_rect.centerx - who.get_width() // 2, layout.modal_rect.y + 84))
        sub = tiny_font.render("wants to duel in the arena", True, TEXT_MUTED)
        surface.blit(sub, (layout.modal_rect.centerx - sub.get_width() // 2, layout.modal_rect.y + 118))

        draw_rounded_button(
            surface,
            layout.challenge_accept,
            "Accept",
            font,
            bg=SUCCESS,
            bg_hover=SUCCESS_HOVER,
            bg_pressed=SUCCESS,
            mouse_pos=mouse_pos,
            mouse_down=mouse_down,
            border_color=BORDER,
        )
        draw_rounded_button(
            surface,
            layout.challenge_reject,
            "Decline",
            font,
            bg=DANGER,
            bg_hover=DANGER_HOVER,
            bg_pressed=DANGER,
            mouse_pos=mouse_pos,
            mouse_down=mouse_down,
            border_color=BORDER,
        )
# I use this function to handle lobby mouse.


def handle_lobby_mouse(
    state: LobbyScreenState,
    event: pygame.event.Event,
    surface: pygame.Surface,
    user_entries: list[dict[str, Any]],
    my_username: str,
) -> str | None:
    """Map a left-click to an action: ``select:`` user, play, watch, refresh, or challenge accept/reject."""
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return None

    layout = _layout(surface, user_entries, my_username)

    if state.incoming_challenge_from:
        if layout.challenge_accept.collidepoint(event.pos):
            return "challenge_accept"
        if layout.challenge_reject.collidepoint(event.pos):
            return "challenge_reject"
        return None

    for rect, item in layout.user_rows:
        if rect.collidepoint(event.pos):
            name = str(item.get("username", ""))
            return f"select:{name}"

    if layout.play_rect.collidepoint(event.pos):
        return "play"
    if layout.watch_rect.collidepoint(event.pos):
        return "watch"
    if layout.refresh_rect.collidepoint(event.pos):
        return "refresh"

    return None
