"""
client/ui_theme.py

Shared palette, typography, gradients, and button styling for Pygame screens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

# --- Palette: jewel-tone arena (violet / magenta / cyan + gold π accent) ---
BG_ROOT_TOP: Final[tuple[int, int, int]] = (28, 16, 52)
BG_ROOT_MID: Final[tuple[int, int, int]] = (14, 22, 58)
BG_ROOT_BOTTOM: Final[tuple[int, int, int]] = (6, 12, 36)
BG_ROOT: Final[tuple[int, int, int]] = BG_ROOT_BOTTOM  # solid fallback (ingame)
BG_PANEL: Final[tuple[int, int, int]] = (26, 22, 48)
BG_PANEL_ALT: Final[tuple[int, int, int]] = (20, 18, 42)
BG_INPUT: Final[tuple[int, int, int]] = (34, 28, 58)
BG_INPUT_FOCUS: Final[tuple[int, int, int]] = (42, 34, 72)
ACCENT: Final[tuple[int, int, int]] = (56, 232, 255)  # electric cyan
ACCENT_SOFT: Final[tuple[int, int, int]] = (120, 245, 255)
ACCENT_HOVER: Final[tuple[int, int, int]] = (96, 248, 255)
ACCENT_PRESS: Final[tuple[int, int, int]] = (32, 188, 218)
ACCENT_DIM: Final[tuple[int, int, int]] = (26, 120, 145)
BRAND_MAGENTA: Final[tuple[int, int, int]] = (244, 114, 182)
BRAND_GOLD_PI: Final[tuple[int, int, int]] = (255, 214, 102)
BRAND_VIOLET: Final[tuple[int, int, int]] = (167, 139, 250)
BRAND_WORD: Final[tuple[int, int, int]] = (248, 246, 255)
SECONDARY_BTN: Final[tuple[int, int, int]] = (44, 38, 72)
SECONDARY_HOVER: Final[tuple[int, int, int]] = (56, 48, 92)
SECONDARY_PRESS: Final[tuple[int, int, int]] = (38, 32, 62)
SUCCESS: Final[tuple[int, int, int]] = (74, 222, 158)
SUCCESS_HOVER: Final[tuple[int, int, int]] = (110, 245, 188)
DANGER: Final[tuple[int, int, int]] = (251, 113, 133)
DANGER_HOVER: Final[tuple[int, int, int]] = (255, 148, 165)
TEXT: Final[tuple[int, int, int]] = (248, 246, 255)
TEXT_MUTED: Final[tuple[int, int, int]] = (156, 162, 198)
TEXT_ERROR: Final[tuple[int, int, int]] = (255, 170, 200)
BORDER: Final[tuple[int, int, int]] = (72, 62, 118)
BORDER_ACCENT: Final[tuple[int, int, int]] = (168, 120, 255)
SHADOW: Final[tuple[int, int, int]] = (4, 4, 18)
CORAL: Final[tuple[int, int, int]] = (255, 138, 128)
OVERLAY_SCRIM: Final[tuple[int, int, int, int]] = (12, 8, 28, 220)

GAME_WINDOW_TITLE: Final[str] = "πthon Arena"

WINDOW_SIZE: Final[tuple[int, int]] = (960, 700)

_FONT_NAMES: Final[tuple[str, ...]] = ("Segoe UI", "Arial", "Calibri", "Tahoma")

# Cached gradient background (rebuilt if window size changes)
_bg_cache: pygame.Surface | None = None
_bg_cache_size: tuple[int, int] | None = None
_menu_bg_source: pygame.Surface | None = None
_menu_bg_scaled: pygame.Surface | None = None
_menu_bg_scaled_size: tuple[int, int] | None = None

_MENU_BG_CANDIDATES: Final[tuple[Path, ...]] = (
    Path(__file__).resolve().parents[1] / "assets" / "menu_bg.png",
    Path(
        r"C:\Users\Lenovo\.cursor\projects\c-Users-Lenovo-Desktop-Project-EECE-350\assets\c__Users_Lenovo_AppData_Roaming_Cursor_User_workspaceStorage_b4c9c30635d5364f9703e0982a095b06_images_image-ad338137-e4dd-46b8-9bed-18f279d670ca.png"
    ),
)
# I use this function to load fonts.


def load_fonts() -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    """Title, button/body, caption, tiny caption."""
    title = pygame.font.SysFont(_FONT_NAMES[0], 44, bold=True)
    body = pygame.font.SysFont(_FONT_NAMES[0], 22)
    small = pygame.font.SysFont(_FONT_NAMES[0], 17)
    tiny = pygame.font.SysFont(_FONT_NAMES[0], 14)
    return title, body, small, tiny
# I use this function to fill screen background.


def fill_screen_background(surface: pygame.Surface) -> None:
    """Full-window multi-stop gradient + vignette + soft top accent (cached per size)."""
    global _bg_cache, _bg_cache_size
    w, h = surface.get_size()
    if _bg_cache is None or _bg_cache_size != (w, h):
        _bg_cache = pygame.Surface((w, h))
        _bg_cache_size = (w, h)
        top = BG_ROOT_TOP
        mid = BG_ROOT_MID
        bot = BG_ROOT_BOTTOM
        for y in range(h):
            t = y / max(h - 1, 1)
            if t < 0.5:
                u = t * 2
                r = int(top[0] * (1 - u) + mid[0] * u)
                g = int(top[1] * (1 - u) + mid[1] * u)
                b = int(top[2] * (1 - u) + mid[2] * u)
            else:
                u = (t - 0.5) * 2
                r = int(mid[0] * (1 - u) + bot[0] * u)
                g = int(mid[1] * (1 - u) + bot[1] * u)
                b = int(mid[2] * (1 - u) + bot[2] * u)
            pygame.draw.line(_bg_cache, (r, g, b), (0, y), (w, y))
        vignette = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(
            vignette,
            (40, 20, 80, 55),
            (-int(w * 0.12), -int(h * 0.08), int(w * 1.24), int(h * 1.2)),
        )
        _bg_cache.blit(vignette, (0, 0))
        glow = pygame.Surface((w, 5), pygame.SRCALPHA)
        for x in range(w):
            a = int(28 + 55 * (1.0 - abs(x / max(w - 1, 1) - 0.5) * 2))
            pygame.draw.line(glow, (*BRAND_MAGENTA, min(255, a)), (x, 0), (x, 4))
        _bg_cache.blit(glow, (0, 0))
        sweep = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w, 48):
            pygame.draw.line(sweep, (*ACCENT, 10), (x, 0), (x + h // 3, h))
        _bg_cache.blit(sweep, (0, 0))

    surface.blit(_bg_cache, (0, 0))
# I use this function to draw menu background.


def draw_menu_background(surface: pygame.Surface) -> None:
    """
    Draw menu background art with a readability scrim.

    Falls back to the theme gradient when no image file is available.
    """
    global _menu_bg_source, _menu_bg_scaled, _menu_bg_scaled_size
    fill_screen_background(surface)

    if _menu_bg_source is None:
        for candidate in _MENU_BG_CANDIDATES:
            if candidate.exists():
                try:
                    _menu_bg_source = pygame.image.load(str(candidate)).convert()
                    break
                except pygame.error:
                    _menu_bg_source = None

    if _menu_bg_source is None:
        return

    w, h = surface.get_size()
    if _menu_bg_scaled is None or _menu_bg_scaled_size != (w, h):
        _menu_bg_scaled = pygame.transform.smoothscale(_menu_bg_source, (w, h))
        _menu_bg_scaled_size = (w, h)
    surface.blit(_menu_bg_scaled, (0, 0))

    # Keep foreground UI readable on top of detailed artwork.
    scrim = pygame.Surface((w, h), pygame.SRCALPHA)
    scrim.fill((10, 8, 24, 145))
    surface.blit(scrim, (0, 0))
# I use this function to brand glyphs.


def _brand_glyphs(title_font: pygame.font.Font) -> tuple[pygame.Surface, pygame.Surface, pygame.Surface, pygame.Surface]:
    """``π`` + ``thon`` + space + ``Arena`` (Pi → π for the Python pun)."""
    pi_sym = title_font.render("π", True, BRAND_GOLD_PI)
    thon = title_font.render("thon", True, BRAND_WORD)
    sp = title_font.render(" ", True, BRAND_WORD)
    arena = title_font.render("Arena", True, BRAND_MAGENTA)
    return pi_sym, thon, sp, arena
# I use this function to blit game brand.


def blit_game_brand(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    *,
    cx: int,
    top: int,
) -> int:
    """Centered wordmark ``πthon Arena``. Returns bottom y of the title line."""
    pi_sym, thon, sp, arena = _brand_glyphs(title_font)
    total_w = pi_sym.get_width() + thon.get_width() + sp.get_width() + arena.get_width()
    x = cx - total_w // 2
    surface.blit(pi_sym, (x, top))
    x += pi_sym.get_width()
    surface.blit(thon, (x, top))
    x += thon.get_width()
    surface.blit(sp, (x, top))
    x += sp.get_width()
    surface.blit(arena, (x, top))
    line_h = max(pi_sym.get_height(), thon.get_height(), arena.get_height())
    return top + line_h
# I use this function to blit game brand left.


def blit_game_brand_left(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    *,
    left_x: int,
    top: int,
) -> int:
    """Left-aligned ``πthon Arena`` (e.g. lobby header). Returns bottom y."""
    pi_sym, thon, sp, arena = _brand_glyphs(title_font)
    x = left_x
    surface.blit(pi_sym, (x, top))
    x += pi_sym.get_width()
    surface.blit(thon, (x, top))
    x += thon.get_width()
    surface.blit(sp, (x, top))
    x += sp.get_width()
    surface.blit(arena, (x, top))
    line_h = max(pi_sym.get_height(), thon.get_height(), arena.get_height())
    return top + line_h
# I use this function to measure brand line height.


def measure_brand_line_height(title_font: pygame.font.Font) -> int:
    """Pixel height of the wordmark line for vertical layout in forms."""
    pi_sym, thon, _, arena = _brand_glyphs(title_font)
    return max(pi_sym.get_height(), thon.get_height(), arena.get_height())
# I use this function to wrap text lines.


def wrap_text_lines(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Break text into lines that fit ``max_width`` when rendered with ``font``."""
    words = text.replace("\n", " ").split()
    if not words:
        return []
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        trial = " ".join(cur + [word])
        if font.size(trial)[0] <= max_width:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines
# I use this function to fade surface out.


def fade_surface_out(
    surface: pygame.Surface,
    snapshot: pygame.Surface,
    *,
    duration_ms: int = 480,
    top_rgb: tuple[int, int, int] = (18, 12, 40),
) -> None:
    """Smooth dimming transition for exit (keeps last frame visible under a rising scrim)."""
    clock = pygame.time.Clock()
    w, h = surface.get_size()
    start = pygame.time.get_ticks()
    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    while True:
        # Keep pumping events during the fade so Windows doesn't mark the app as hung.
        pygame.event.pump()
        now = pygame.time.get_ticks()
        u = min(1.0, (now - start) / duration_ms)
        alpha = int(235 * u)
        surface.blit(snapshot, (0, 0))
        veil.fill((*top_rgb, alpha))
        surface.blit(veil, (0, 0))
        pygame.display.flip()
        clock.tick(60)
        if u >= 1.0:
            break
# I use this function to draw panel.


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    bg: tuple[int, int, int] = BG_PANEL,
    border_color: tuple[int, int, int] = BORDER,
    radius: int = 14,
    accent_top: bool = False,
) -> None:
    """Fill a rounded rectangle with optional thin accent strip under the top edge."""
    pygame.draw.rect(surface, bg, rect, border_radius=radius)
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=radius)
    if accent_top:
        strip = pygame.Rect(rect.x + radius // 2, rect.y + 2, rect.width - radius, 3)
        pygame.draw.rect(surface, BORDER_ACCENT, strip, border_radius=2)
# I use this function to draw card shadow.


def draw_card_shadow(surface: pygame.Surface, rect: pygame.Rect, radius: int = 16) -> None:
    """Soft offset shadow under cards and modals."""
    shadow = rect.copy()
    shadow.y += 5
    shadow.x += 2
    s = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*SHADOW, 110), s.get_rect(), border_radius=radius)
    surface.blit(s, (shadow.x, shadow.y))
# I use this function to draw rounded button.


def draw_rounded_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    font: pygame.font.Font,
    *,
    bg: tuple[int, int, int],
    bg_hover: tuple[int, int, int],
    bg_pressed: tuple[int, int, int] | None = None,
    text_color: tuple[int, int, int] = TEXT,
    mouse_pos: tuple[int, int] | None = None,
    mouse_down: bool = False,
    radius: int = 11,
    border_color: tuple[int, int, int] | None = None,
    shadow: bool = True,
    glow_accent: bool = False,
) -> None:
    """Primary-style button: hover/press fills, drop shadow, centered label, optional glow border."""
    hover = mouse_pos is not None and rect.collidepoint(mouse_pos)
    pressed = hover and mouse_down
    fill = bg_pressed if (pressed and bg_pressed is not None) else (bg_hover if hover else bg)

    if shadow and not pressed:
        sh = rect.copy()
        sh.y += 3
        sh_r = radius
        pygame.draw.rect(surface, SHADOW, sh, border_radius=sh_r)

    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    # Top highlight (glass edge)
    hi = pygame.Rect(rect.x + 4, rect.y + 3, rect.width - 8, max(2, radius // 2))
    if hover and not pressed:
        gleam = pygame.Surface((hi.width, hi.height), pygame.SRCALPHA)
        gleam.fill((255, 255, 255, 22))
        surface.blit(gleam, hi.topleft)
    if glow_accent and hover:
        pygame.draw.rect(surface, ACCENT_SOFT, rect, width=2, border_radius=radius)
    elif border_color:
        pygame.draw.rect(surface, border_color, rect, width=1, border_radius=radius)

    surf = font.render(text, True, text_color)
    text_offset_y = 1 if pressed else 0
    surface.blit(
        surf,
        (
            rect.centerx - surf.get_width() // 2,
            rect.centery - surf.get_height() // 2 + text_offset_y,
        ),
    )
# I use this function to draw outline button.


def draw_outline_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    font: pygame.font.Font,
    *,
    fg: tuple[int, int, int] = ACCENT,
    fg_hover: tuple[int, int, int] = ACCENT_SOFT,
    bg_idle: tuple[int, int, int] = BG_PANEL_ALT,
    bg_hover: tuple[int, int, int] = SECONDARY_HOVER,
    mouse_pos: tuple[int, int] | None = None,
    mouse_down: bool = False,
    radius: int = 11,
) -> None:
    """Secondary-style button: lighter fill, border thickens on hover, centered text."""
    hover = mouse_pos is not None and rect.collidepoint(mouse_pos)
    pressed = hover and mouse_down
    fill = bg_hover if hover else bg_idle
    col = fg_hover if hover else fg

    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    w = 2 if hover else 1
    pygame.draw.rect(surface, BORDER_ACCENT if hover else BORDER, rect, width=w, border_radius=radius)

    surf = font.render(text, True, col)
    dy = 1 if pressed else 0
    surface.blit(
        surf,
        (rect.centerx - surf.get_width() // 2, rect.centery - surf.get_height() // 2 + dy),
    )
# I use this function to draw pill label.


def draw_pill_label(
    surface: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    font: pygame.font.Font,
    *,
    bg: tuple[int, int, int] = BG_PANEL_ALT,
    text_color: tuple[int, int, int] = ACCENT,
) -> None:
    """A pill-shaped read-only label (e.g. mode tag) with centered text."""
    pygame.draw.rect(surface, bg, rect, border_radius=rect.height // 2)
    pygame.draw.rect(surface, BORDER, rect, width=1, border_radius=rect.height // 2)
    s = font.render(text, True, text_color)
    surface.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - s.get_height() // 2))
# I use this function to draw toast.


def draw_toast(surface: pygame.Surface, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
    """A warm coral-outlined bar for short transient messages (e.g. server errors)."""
    pygame.draw.rect(surface, (38, 32, 28), rect, border_radius=12)
    pygame.draw.rect(surface, CORAL, rect, width=1, border_radius=12)
    ts = font.render(text[:120], True, (255, 230, 210))
    surface.blit(ts, (rect.centerx - ts.get_width() // 2, rect.centery - ts.get_height() // 2))
