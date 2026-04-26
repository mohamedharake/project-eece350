"""
client/screens/connect_screen.py

Login / connection screen: optional host & port behind "Custom server", username, Connect.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from client.ui_theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESS,
    BG_INPUT,
    BG_INPUT_FOCUS,
    BG_PANEL,
    BORDER,
    BORDER_ACCENT,
    BRAND_VIOLET,
    SHADOW,
    TEXT,
    TEXT_ERROR,
    TEXT_MUTED,
    blit_game_brand,
    draw_card_shadow,
    draw_panel,
    draw_pill_label,
    draw_rounded_button,
    draw_menu_background,
    measure_brand_line_height,
    wrap_text_lines,
)
from shared.constants import MAX_USERNAME_LEN


@dataclass
class LoginScreenState:
    host: str = "127.0.0.1"
    port_text: str = "5000"
    username: str = ""
    focus_field: int = 2  # 0=host, 1=port, 2=username when advanced_server is True
    advanced_server: bool = False
    error_message: str = ""
    snake_style: str = "cyan"
    control_scheme: str = "ARROWS"
    # I use this function to cycle focus.

    def cycle_focus(self) -> None:
        """Advance Tab focus among host, port, and username (or only username in simple mode)."""
        if self.advanced_server:
            self.focus_field = (self.focus_field + 1) % 3
        else:
            self.focus_field = 2


@dataclass(frozen=True)
class ConnectLayout:
    card: pygame.Rect
    host_r: pygame.Rect | None
    port_r: pygame.Rect | None
    user_r: pygame.Rect
    connect_r: pygame.Rect
    toggle_server_rect: pygame.Rect
    style_rect: pygame.Rect
    controls_rect: pygame.Rect
    subtitle_lines: tuple[str, ...]
    subtitle_y: int
    pill_rect: pygame.Rect


SNAKE_STYLE_OPTIONS: tuple[tuple[str, str, tuple[int, int, int]], ...] = (
    ("cyan", "Cyan", (56, 226, 255)),
    ("lime", "Lime", (167, 243, 125)),
    ("rose", "Rose", (244, 114, 182)),
    ("amber", "Amber", (250, 204, 75)),
    ("violet", "Violet", (196, 181, 253)),
)

CONTROL_OPTIONS: tuple[str, ...] = ("ARROWS", "WASD")
# I use this function to fit text.


def _fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Trim text to fit a target render width."""
    if font.size(text)[0] <= max_width:
        return text
    base = text
    while base and font.size(base + "...")[0] > max_width:
        base = base[:-1]
    return (base + "...") if base else ""
# I use this function to compute connect layout.


def compute_connect_layout(
    surface: pygame.Surface,
    state: LoginScreenState,
    *,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
) -> ConnectLayout:
    """Single source of truth for connect screen geometry (draw + hit testing)."""
    w, h = surface.get_size()
    card_w = min(520, w - 72)
    inner_left_pad = 36
    field_w = card_w - 72
    field_h = 46
    field_gap = 54

    subtitle = (
        "Custom host and port — only if you are not using the default server."
        if state.advanced_server
        else "Choose my display name. Use “Custom server” below only if needed."
    )
    sub_max = max(180, card_w - 56)
    sub_lines = wrap_text_lines(small_font, subtitle, sub_max)
    line_stride = small_font.get_height() + 4
    subtitle_block_h = len(sub_lines) * line_stride - 4

    brand_margin_top = 26
    brand_h = measure_brand_line_height(title_font)
    pill_h = 28
    gap_brand_pill = 12
    gap_pill_sub = 10
    gap_sub_fields = 20
    label_above_field = 22

    card_top = max(24, (h - 600) // 2 - 12)
    card = pygame.Rect((w - card_w) // 2, card_top, card_w, 400)
    inner_left = card.x + inner_left_pad

    brand_top = card.y + brand_margin_top
    brand_bottom = brand_top + brand_h
    pill_rect = pygame.Rect(card.centerx - 118, brand_bottom + gap_brand_pill, 236, pill_h)
    subtitle_y = pill_rect.bottom + gap_pill_sub

    fields_top = subtitle_y + subtitle_block_h + gap_sub_fields + label_above_field

    if state.advanced_server:
        host_r = pygame.Rect(inner_left, fields_top, field_w, field_h)
        port_r = pygame.Rect(inner_left, fields_top + field_gap, field_w, field_h)
        user_r = pygame.Rect(inner_left, fields_top + 2 * field_gap, field_w, field_h)
        connect_r = pygame.Rect(card.centerx - 122, user_r.bottom + 28, 244, 54)
        host_r_out: pygame.Rect | None = host_r
        port_r_out: pygame.Rect | None = port_r
    else:
        host_r_out = None
        port_r_out = None
        user_r = pygame.Rect(inner_left, fields_top, field_w, field_h)
        connect_r = pygame.Rect(card.centerx - 130, user_r.bottom + 44, 260, 56)

    style_rect = pygame.Rect(inner_left, user_r.bottom + 26, field_w, 38)
    controls_rect = pygame.Rect(inner_left, style_rect.bottom + 24, field_w, 38)
    connect_r.y = controls_rect.bottom + 22

    toggle_server_rect = pygame.Rect(card.centerx - 176, connect_r.bottom + 26, 352, 40)

    content_bottom = toggle_server_rect.bottom
    card.height = max(content_bottom - card.y + 26, 320)

    # Keep card comfortably above the footer bar.
    shift = max(0, card.bottom + 14 - (h - 72))
    if shift:
        card.y -= shift
        pill_rect.y -= shift
        subtitle_y -= shift
        user_r.y -= shift
        if host_r_out:
            host_r_out.y -= shift
        if port_r_out:
            port_r_out.y -= shift
        connect_r.y -= shift
        style_rect.y -= shift
        controls_rect.y -= shift
        toggle_server_rect.y -= shift

    return ConnectLayout(
        card=card,
        host_r=host_r_out,
        port_r=port_r_out,
        user_r=user_r,
        connect_r=connect_r,
        toggle_server_rect=toggle_server_rect,
        style_rect=style_rect,
        controls_rect=controls_rect,
        subtitle_lines=tuple(sub_lines),
        subtitle_y=subtitle_y,
        pill_rect=pill_rect,
    )
# I use this function to hit.


def _hit(rect: pygame.Rect, pos: tuple[int, int]) -> bool:
    """True if ``pos`` is inside ``rect`` (mouse hit test)."""
    return rect.collidepoint(pos)
# I use this function to draw login.


def draw_login(
    surface: pygame.Surface,
    state: LoginScreenState,
    *,
    title_font: pygame.font.Font,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    tiny_font: pygame.font.Font,
    mouse_pos: tuple[int, int] | None = None,
) -> None:
    """Render the connect card: brand, fields, style/controls, connect button, and footer hint."""
    draw_menu_background(surface)
    mouse_down = bool(pygame.mouse.get_pressed()[0])

    lay = compute_connect_layout(surface, state, title_font=title_font, small_font=small_font)

    draw_card_shadow(surface, lay.card)
    draw_panel(surface, lay.card, bg=BG_PANEL, border_color=BORDER, radius=20, accent_top=True)

    blit_game_brand(surface, title_font, cx=lay.card.centerx, top=lay.card.y + 26)

    draw_pill_label(
        surface,
        lay.pill_rect,
        "MULTIPLAYER SNAKE BATTLE",
        tiny_font,
        text_color=TEXT_MUTED,
    )

    sy = lay.subtitle_y
    for line in lay.subtitle_lines:
        surf = small_font.render(line, True, TEXT_MUTED)
        surface.blit(surf, (lay.card.centerx - surf.get_width() // 2, sy))
        sy += small_font.get_height() + 4

    labels_and_rects: list[tuple[str, pygame.Rect, str]]
    if state.advanced_server and lay.host_r and lay.port_r:
        labels_and_rects = [
            ("Server host", lay.host_r, state.host),
            ("Server port", lay.port_r, state.port_text),
            ("Username", lay.user_r, state.username),
        ]
    else:
        labels_and_rects = [("Username", lay.user_r, state.username)]

    for i, (label, rect, text) in enumerate(labels_and_rects):
        field_idx = (0, 1, 2)[i] if state.advanced_server else 2
        lbl = small_font.render(label.upper(), True, TEXT)
        surface.blit(lbl, (rect.x, rect.y - 24))
        bg = BG_INPUT_FOCUS if state.focus_field == field_idx else BG_INPUT
        pygame.draw.rect(surface, SHADOW, (rect.x + 2, rect.y + 4, rect.width, rect.height), border_radius=12)
        pygame.draw.rect(surface, bg, rect, border_radius=12)
        brd = BORDER_ACCENT if state.focus_field == field_idx else BORDER
        pygame.draw.rect(surface, brd, rect, width=2 if state.focus_field == field_idx else 1, border_radius=12)
        display = text + ("|" if state.focus_field == field_idx else "")
        fitted_display = _fit_text(font, display, rect.width - 24)
        txt_surf = font.render(fitted_display, True, TEXT)
        surface.blit(txt_surf, (rect.x + 14, rect.y + (rect.height - txt_surf.get_height()) // 2))

    style_label = small_font.render("SNAKE COLOR", True, TEXT)
    surface.blit(style_label, (lay.style_rect.x, lay.style_rect.y - 24))
    pygame.draw.rect(surface, SHADOW, (lay.style_rect.x + 2, lay.style_rect.y + 3, lay.style_rect.width, lay.style_rect.height), border_radius=10)
    pygame.draw.rect(surface, BG_INPUT, lay.style_rect, border_radius=10)
    pygame.draw.rect(surface, BORDER, lay.style_rect, width=1, border_radius=10)
    style_name = next((label for key, label, _ in SNAKE_STYLE_OPTIONS if key == state.snake_style), "Cyan")
    style_color = next((c for key, _, c in SNAKE_STYLE_OPTIONS if key == state.snake_style), (56, 226, 255))
    swatch = pygame.Rect(lay.style_rect.x + 12, lay.style_rect.y + 9, 20, 20)
    pygame.draw.rect(surface, style_color, swatch, border_radius=6)
    pygame.draw.rect(surface, (255, 255, 255), swatch, width=1, border_radius=6)
    style_txt = font.render(_fit_text(font, f"{style_name}  (click to change)", lay.style_rect.width - 52), True, TEXT)
    surface.blit(style_txt, (lay.style_rect.x + 42, lay.style_rect.y + (lay.style_rect.height - style_txt.get_height()) // 2))

    controls_label = small_font.render("CONTROLS", True, TEXT)
    surface.blit(controls_label, (lay.controls_rect.x, lay.controls_rect.y - 24))
    pygame.draw.rect(
        surface,
        SHADOW,
        (lay.controls_rect.x + 2, lay.controls_rect.y + 3, lay.controls_rect.width, lay.controls_rect.height),
        border_radius=10,
    )
    pygame.draw.rect(surface, BG_INPUT, lay.controls_rect, border_radius=10)
    pygame.draw.rect(surface, BORDER, lay.controls_rect, width=1, border_radius=10)
    controls_txt = font.render(
        _fit_text(font, f"{state.control_scheme}  (click to switch)", lay.controls_rect.width - 24),
        True,
        TEXT,
    )
    surface.blit(
        controls_txt,
        (lay.controls_rect.x + 14, lay.controls_rect.y + (lay.controls_rect.height - controls_txt.get_height()) // 2),
    )

    draw_rounded_button(
        surface,
        lay.connect_r,
        "Enter arena",
        font,
        bg=ACCENT,
        bg_hover=ACCENT_HOVER,
        bg_pressed=ACCENT_PRESS,
        mouse_pos=mouse_pos,
        mouse_down=mouse_down,
        border_color=BORDER_ACCENT,
        glow_accent=True,
    )

    toggle_hover = mouse_pos is not None and lay.toggle_server_rect.collidepoint(mouse_pos)
    toggle_txt = "Hide server settings" if state.advanced_server else "Custom server address & port…"
    tc = BRAND_VIOLET if toggle_hover else ACCENT
    toggle_surf = small_font.render(_fit_text(small_font, toggle_txt, lay.toggle_server_rect.width - 10), True, tc)
    tx = lay.toggle_server_rect.centerx - toggle_surf.get_width() // 2
    ty = lay.toggle_server_rect.centery - toggle_surf.get_height() // 2
    surface.blit(toggle_surf, (tx, ty))
    if toggle_hover:
        pygame.draw.line(
            surface,
            BRAND_VIOLET,
            (tx, ty + toggle_surf.get_height() + 2),
            (tx + toggle_surf.get_width(), ty + toggle_surf.get_height() + 2),
            1,
        )

    if state.error_message:
        err = small_font.render(state.error_message[:160], True, TEXT_ERROR)
        err_y = min(lay.toggle_server_rect.bottom + 12, surface.get_height() - 70)
        surface.blit(err, (lay.card.centerx - err.get_width() // 2, err_y))

    foot_h = 52
    footer = pygame.Rect(0, surface.get_height() - foot_h, surface.get_width(), foot_h)
    bar = pygame.Surface((footer.width, footer.height), pygame.SRCALPHA)
    bar.fill((22, 14, 42, 248))
    surface.blit(bar, footer.topleft)
    pygame.draw.line(surface, BORDER, (0, footer.y), (footer.width, footer.y), 1)
    hint = tiny_font.render("Tab — next field   ·   Enter — connect", True, TEXT_MUTED)
    surface.blit(hint, ((surface.get_width() - hint.get_width()) // 2, surface.get_height() - 28))
# I use this function to append char.


def _append_char(state: LoginScreenState, ch: str) -> None:
    """Append one typed character to the focused field, respecting length limits."""
    if state.focus_field == 0:
        if len(state.host) < 64:
            state.host += ch
    elif state.focus_field == 1:
        if ch.isdigit() and len(state.port_text) < 6:
            state.port_text += ch
    else:
        if len(state.username) < MAX_USERNAME_LEN:
            state.username += ch
# I use this function to handle login events.


def handle_login_events(
    state: LoginScreenState,
    event: pygame.event.Event,
    surface: pygame.Surface,
    *,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
) -> bool:
    """
    Process one event: focus clicks, field typing, advanced toggle.

    Return True if the user should attempt connection (Enter or Connect click).
    """
    lay = compute_connect_layout(surface, state, title_font=title_font, small_font=small_font)

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if _hit(lay.connect_r, event.pos):
            return True
        if _hit(lay.toggle_server_rect, event.pos):
            state.advanced_server = not state.advanced_server
            if state.advanced_server:
                state.focus_field = 0
            else:
                state.focus_field = 2
            return False
        if _hit(lay.style_rect, event.pos):
            current_idx = 0
            for idx, (key, _, _) in enumerate(SNAKE_STYLE_OPTIONS):
                if key == state.snake_style:
                    current_idx = idx
                    break
            state.snake_style = SNAKE_STYLE_OPTIONS[(current_idx + 1) % len(SNAKE_STYLE_OPTIONS)][0]
            return False
        if _hit(lay.controls_rect, event.pos):
            state.control_scheme = "WASD" if state.control_scheme.upper() == "ARROWS" else "ARROWS"
            return False
        if state.advanced_server and lay.host_r and _hit(lay.host_r, event.pos):
            state.focus_field = 0
        elif state.advanced_server and lay.port_r and _hit(lay.port_r, event.pos):
            state.focus_field = 1
        elif _hit(lay.user_r, event.pos):
            state.focus_field = 2
        return False

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_TAB:
            state.cycle_focus()
            return False
        if event.key == pygame.K_RETURN:
            return True
        if event.key == pygame.K_BACKSPACE:
            if state.focus_field == 0 and state.host:
                state.host = state.host[:-1]
            elif state.focus_field == 1 and state.port_text:
                state.port_text = state.port_text[:-1]
            elif state.focus_field == 2 and state.username:
                state.username = state.username[:-1]
            return False
        if event.unicode and event.unicode.isprintable() and event.unicode not in {"\r", "\n"}:
            _append_char(state, event.unicode)
        return False

    return False
