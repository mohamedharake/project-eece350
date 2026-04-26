"""
client/screens/game_screen.py

In-game Pygame screen for Phase F.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Literal

import pygame

from client.input_config import keymap_for_controls
from client.render import draw_state, draw_waiting_for_state, window_size_from_state
from client.ui_theme import GAME_WINDOW_TITLE, fade_surface_out

GameScreenResult = Literal["quit", "game_over", "leave_match"]
# I use this function to run game screen.


def run_game_screen(
    *,
    my_username: str,
    get_latest_state: Callable[[], dict[str, Any] | None],
    get_game_over: Callable[[], dict[str, Any] | None],
    send_move: Callable[[str], None],
    send_chat: Callable[[str], None],
    get_chat_messages: Callable[[], list[dict[str, Any]]],
    is_spectator: bool = False,
    manage_pygame_lifecycle: bool = True,
    exit_on_game_over: bool = False,
    show_game_over_overlay: bool = True,
    esc_leaves_match: bool = False,
    control_scheme: str = "ARROWS",
) -> GameScreenResult:
    """
    Run the live game view until closed, game over (optional), or ESC (optional lobby).

    If ``esc_leaves_match`` is True, ESC (when chat is inactive) disconnects via the
    outer app's reconnect flow rather than quitting the entire process — used by GUI only.
    """
    if manage_pygame_lifecycle:
        pygame.init()
        pygame.font.init()

    clock = pygame.time.Clock()
    window = pygame.display.set_mode(window_size_from_state(None))
    pygame.display.set_caption(f"{GAME_WINDOW_TITLE} — {my_username}")

    running = True
    chat_active = False
    chat_buffer: list[str] = []
    last_resize = 0.0
    result: GameScreenResult = "quit"
    key_to_direction = keymap_for_controls(control_scheme)

    while running:
        # Highest priority: match ended -> stop gameplay loop immediately for GUI handoff.
        game_over_payload = get_game_over()
        if exit_on_game_over and game_over_payload is not None:
            result = "game_over"
            running = False
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                result = "quit"
                break
            if event.type == pygame.KEYDOWN:
                if chat_active:
                    if event.key == pygame.K_RETURN:
                        text = "".join(chat_buffer).strip()
                        if text:
                            send_chat(text)
                        chat_buffer.clear()
                        chat_active = False
                        break
                    if event.key == pygame.K_ESCAPE:
                        chat_buffer.clear()
                        chat_active = False
                        break
                    if event.key == pygame.K_BACKSPACE:
                        if chat_buffer:
                            chat_buffer.pop()
                        break
                    if event.key == pygame.K_TAB:
                        break
                    if event.unicode and event.unicode.isprintable() and event.unicode not in {"\r", "\n"}:
                        if len(chat_buffer) < 256:
                            chat_buffer.append(event.unicode)
                        break
                else:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        result = "leave_match" if esc_leaves_match else "quit"
                        break
                    if event.key == pygame.K_RETURN:
                        chat_active = True
                        chat_buffer.clear()
                        break
                    direction = key_to_direction.get(event.key)
                    if direction and not is_spectator:
                        send_move(direction)

        if exit_on_game_over:
            game_over_payload = get_game_over()
            if game_over_payload is not None:
                result = "game_over"
                running = False
                break

        state_payload = get_latest_state()
        desired_size = window_size_from_state(state_payload)
        now = time.monotonic()
        if window.get_size() != desired_size and now - last_resize > 0.2:
            window = pygame.display.set_mode(desired_size)
            last_resize = now

        if state_payload is None:
            draw_waiting_for_state(window, "Waiting for game state from server…")
        else:
            draw_state(
                window,
                state_payload,
                my_username=my_username,
                game_over_payload=game_over_payload if show_game_over_overlay else None,
                chat_messages=get_chat_messages(),
                chat_input="".join(chat_buffer),
                chat_active=chat_active,
                is_spectator=is_spectator,
                show_game_over_overlay=show_game_over_overlay,
                hud_esc_hint_leaves_match=esc_leaves_match,
                control_scheme=control_scheme,
            )

        pygame.display.flip()
        clock.tick(60)

    snapshot = window.copy()
    fade_surface_out(window, snapshot)

    if manage_pygame_lifecycle:
        pygame.quit()

    return result
