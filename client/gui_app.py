"""
client/gui_app.py

Pygame screen manager: LOGIN → LOBBY → GAME → GAME_OVER (loop).
Networking matches ``net_client``; protocol unchanged.
"""

from __future__ import annotations

import threading
from enum import Enum, auto
from typing import Any

import pygame
from pathlib import Path

from client.net_client import ClientConnection
from client.screens.connect_screen import LoginScreenState, draw_login, handle_login_events
from client.screens.game_over_screen import draw_game_over, handle_game_over_event
from client.screens.game_screen import run_game_screen
from client.screens.lobby_screen import LobbyScreenState, draw_lobby, handle_lobby_mouse
from client.ui_theme import GAME_WINDOW_TITLE, WINDOW_SIZE, load_fonts
from shared.protocol import (
    MSG_CHALLENGE_REQUEST,
    MSG_CHALLENGE_RESPONSE,
    MSG_ERROR,
    MSG_GAME_OVER,
    MSG_GAME_STATE,
    MSG_MATCH_START,
    MSG_CHAT_RECV,
    MSG_WATCH_OK,
    MSG_WATCH_ERROR,
    MSG_USER_LIST,
)


class AppPhase(Enum):
    LOGIN = auto()
    LOBBY = auto()
    GAME = auto()
    GAME_OVER = auto()


WINDOW_TITLE = GAME_WINDOW_TITLE
# I use this function to toast.


def _toast(lobby: LobbyScreenState, message: str, ticks: int, duration_ms: int = 4500) -> None:
    """Show a temporary banner on the lobby until ``ticks + duration_ms`` (Pygame clock ms)."""
    lobby.toast_message = message
    lobby.toast_until_ms = ticks + duration_ms
# I use this function to run gui app.


def run_gui_app(*, host: str, port: int, username_prefill: str | None) -> None:
    """Run the full Pygame app: login → lobby → match → game-over loop until exit."""
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    pygame.mixer.init()

    music_path = Path(__file__).resolve().parents[1] / "assets" / "bg.wav"
    pygame.mixer.music.load(str(music_path))
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)

    title_font, font, small_font, tiny_font = load_fonts()

    phase = AppPhase.LOGIN
    login_state = LoginScreenState(host=host, port_text=str(port), username=(username_prefill or "").strip())

    conn: ClientConnection | None = None
    my_username = ""
    receiver_thread: threading.Thread | None = None
    receiver_done = threading.Event()

    saved_host = host.strip()
    saved_port_text = str(port)
    saved_registered_username = ""
    saved_snake_style = login_state.snake_style
    saved_control_scheme = login_state.control_scheme

    state_lock = threading.Lock()
    shared_state: dict[str, Any] = {
        "latest_game_state": None,
        "latest_game_over": None,
        "latest_users": [],
        "match_start_payload": None,
        "chat_messages": [],
    }

    challenge_lock = threading.Lock()
    challenge_queue: list[str] = []

    accept_challenges = threading.Event()

    spectator_mode = {"value": False}
    in_match_event = threading.Event()
    match_over_event = threading.Event()

    lobby_state = LobbyScreenState()
    # I use this function to on message.

    def on_message(msg: dict) -> None:
        """Handle one server message: update shared UI state, toasts, and phase flags."""
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == MSG_USER_LIST:
            users = payload.get("users", [])
            with state_lock:
                shared_state["latest_users"] = users
            return

        if msg_type == MSG_CHALLENGE_REQUEST:
            if not accept_challenges.is_set():
                return
            challenger = payload.get("from", "")
            if challenger:
                with challenge_lock:
                    challenge_queue.append(challenger)
            return

        if msg_type == MSG_CHALLENGE_RESPONSE and not payload.get("accepted", False):
            who = payload.get("from", "unknown")
            _toast(lobby_state, f"Challenge declined by '{who}'.", pygame.time.get_ticks())
            return

        if msg_type == MSG_MATCH_START:
            with challenge_lock:
                challenge_queue.clear()
            with state_lock:
                shared_state["match_start_payload"] = payload
            spectator_mode["value"] = False
            in_match_event.set()
            return

        if msg_type == MSG_WATCH_OK:
            with challenge_lock:
                challenge_queue.clear()
            with state_lock:
                shared_state["match_start_payload"] = payload
            spectator_mode["value"] = True
            in_match_event.set()
            return

        if msg_type == MSG_WATCH_ERROR:
            detail = payload.get("detail", "Watch request denied.")
            _toast(lobby_state, detail, pygame.time.get_ticks())
            return

        if msg_type == MSG_GAME_STATE:
            with state_lock:
                shared_state["latest_game_state"] = payload
            return

        if msg_type == MSG_CHAT_RECV:
            chat_from = payload.get("from", "?")
            text = payload.get("text", "")
            with state_lock:
                shared_state["chat_messages"].append({"from": chat_from, "text": text})
                if len(shared_state["chat_messages"]) > 50:
                    shared_state["chat_messages"] = shared_state["chat_messages"][-50:]
            return

        if msg_type == MSG_GAME_OVER:
            with state_lock:
                shared_state["latest_game_over"] = payload
            match_over_event.set()
            return

        if msg_type == MSG_ERROR:
            detail = payload.get("detail", "Server error.")
            _toast(lobby_state, detail, pygame.time.get_ticks())
            return
    # I use this function to receiver worker.

    def receiver_worker() -> None:
        """Background loop: read NDJSON until disconnect; mark ``receiver_done`` when done."""
        try:
            if conn:
                conn.receive_forever(on_message)
        finally:
            receiver_done.set()
    # I use this function to try login.

    def try_login() -> bool:
        """Validate fields, connect, register, start receiver, enable challenges; or set error string."""
        nonlocal conn, my_username, receiver_thread, saved_host, saved_port_text, saved_registered_username
        nonlocal saved_snake_style, saved_control_scheme
        login_state.error_message = ""
        try:
            port_n = int(login_state.port_text.strip())
        except ValueError:
            login_state.error_message = "Invalid port number."
            return False

        host_s = login_state.host.strip()
        user_s = login_state.username.strip()
        if not user_s:
            login_state.error_message = "Enter a username."
            return False

        try:
            new_conn = ClientConnection.connect(host_s, port_n)
        except OSError as exc:
            login_state.error_message = f"Could not connect: {exc}"
            return False

        ok, msg = new_conn.register_username(
            user_s,
            snake_style=login_state.snake_style,
            control_scheme=login_state.control_scheme,
        )
        if not ok:
            new_conn.close()
            login_state.error_message = msg
            return False

        conn = new_conn
        my_username = msg
        saved_host = host_s
        saved_port_text = login_state.port_text.strip()
        saved_registered_username = my_username
        saved_snake_style = login_state.snake_style
        saved_control_scheme = login_state.control_scheme
        receiver_done.clear()
        receiver_thread = threading.Thread(target=receiver_worker, daemon=True)
        receiver_thread.start()
        conn.request_user_list()
        accept_challenges.set()
        with state_lock:
            shared_state["chat_messages"] = []
        return True
    # I use this function to reconnect after leave match.

    def reconnect_after_leave_match() -> bool:
        """Tear down the socket, reconnect, and re-register the same user after ESC from a match."""
        nonlocal conn, my_username, receiver_thread
        cleanup_disconnect()
        try:
            port_n = int(saved_port_text)
            new_conn = ClientConnection.connect(saved_host, port_n)
        except (OSError, ValueError):
            return False

        ok, msg = new_conn.register_username(
            saved_registered_username,
            snake_style=saved_snake_style,
            control_scheme=saved_control_scheme,
        )
        if not ok:
            new_conn.close()
            return False

        conn = new_conn
        my_username = msg
        receiver_done.clear()
        receiver_thread = threading.Thread(target=receiver_worker, daemon=True)
        receiver_thread.start()
        with state_lock:
            shared_state["latest_game_state"] = None
            shared_state["latest_game_over"] = None
            shared_state["match_start_payload"] = None
        with challenge_lock:
            challenge_queue.clear()
        lobby_state.incoming_challenge_from = None
        conn.request_user_list()
        accept_challenges.set()
        with state_lock:
            shared_state["chat_messages"] = []
        return True
    # I use this function to cleanup disconnect.

    def cleanup_disconnect() -> None:
        """Stop accepting challenges, close the socket, and wait briefly for the receiver thread."""
        nonlocal conn, receiver_thread
        accept_challenges.clear()
        if conn:
            conn.close()
            conn = None
        # Receiver thread is daemonized, but join briefly to avoid shutdown races.
        if receiver_thread and receiver_thread.is_alive():
            receiver_thread.join(timeout=0.4)
        receiver_thread = None
    # I use this function to reset to lobby surface.

    def reset_to_lobby_surface() -> None:
        """Re-create the default window and title after returning from the game surface."""
        nonlocal screen
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption(WINDOW_TITLE)

    running = True
    while running:
        if phase == AppPhase.GAME:
            assert conn is not None
            # I use this function to get latest state.

            def get_latest_state() -> dict[str, Any] | None:
                """Latest ``game_state`` for rendering (thread-safe)."""
                with state_lock:
                    return shared_state["latest_game_state"]
            # I use this function to get game over.

            def get_game_over() -> dict[str, Any] | None:
                """Final game-over payload if the match has ended; used for optional early exit."""
                with state_lock:
                    return shared_state["latest_game_over"]
            # I use this function to get chat messages.

            def get_chat_messages() -> list[dict[str, Any]]:
                """Copy of in-match chat lines for the overlay."""
                with state_lock:
                    return list(shared_state["chat_messages"])

            outcome = run_game_screen(
                my_username=my_username,
                get_latest_state=get_latest_state,
                get_game_over=get_game_over,
                send_move=conn.send_move,
                send_chat=conn.send_chat,
                get_chat_messages=get_chat_messages,
                is_spectator=spectator_mode["value"],
                manage_pygame_lifecycle=False,
                exit_on_game_over=True,
                show_game_over_overlay=False,
                esc_leaves_match=True,
                control_scheme=saved_control_scheme,
            )
            if outcome == "quit":
                running = False
                continue
            if outcome == "leave_match":
                reset_to_lobby_surface()
                if reconnect_after_leave_match():
                    lobby_state = LobbyScreenState()
                    phase = AppPhase.LOBBY
                else:
                    login_state.error_message = "Could not reconnect. Check server and try Connect again."
                    phase = AppPhase.LOGIN
                continue

            reset_to_lobby_surface()
            phase = AppPhase.GAME_OVER
            continue

        ticks = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        if phase == AppPhase.LOBBY:
            with challenge_lock:
                lobby_state.incoming_challenge_from = challenge_queue[0] if challenge_queue else None

            if in_match_event.is_set():
                in_match_event.clear()
                match_over_event.clear()
                accept_challenges.clear()
                with state_lock:
                    shared_state["latest_game_over"] = None
                    shared_state["latest_game_state"] = None
                phase = AppPhase.GAME
                continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if phase == AppPhase.LOGIN:
                if handle_login_events(login_state, event, screen, title_font=title_font, small_font=small_font):
                    if try_login():
                        lobby_state = LobbyScreenState()
                        phase = AppPhase.LOBBY

            elif phase == AppPhase.LOBBY:
                assert conn is not None
                with state_lock:
                    users = list(shared_state["latest_users"])

                action = handle_lobby_mouse(lobby_state, event, screen, users, my_username)
                if action == "challenge_accept" and lobby_state.incoming_challenge_from:
                    with challenge_lock:
                        ch = challenge_queue.pop(0) if challenge_queue else ""
                    if ch:
                        conn.send_challenge_response(ch, accepted=True)
                elif action == "challenge_reject" and lobby_state.incoming_challenge_from:
                    with challenge_lock:
                        ch = challenge_queue.pop(0) if challenge_queue else ""
                    if ch:
                        conn.send_challenge_response(ch, accepted=False)
                elif action and not lobby_state.incoming_challenge_from:
                    if action.startswith("select:"):
                        lobby_state.selected_username = action.split(":", 1)[1]
                    elif action == "refresh":
                        conn.request_user_list()
                    elif action == "play":
                        target = lobby_state.selected_username
                        if not target:
                            _toast(lobby_state, "Select a player first.", ticks)
                        else:
                            conn.send_challenge_request(target)
                    elif action == "watch":
                        conn.send_watch_request()

            elif phase == AppPhase.GAME_OVER:
                action = handle_game_over_event(event, screen)
                if action == "lobby":
                    with state_lock:
                        shared_state["latest_game_state"] = None
                        shared_state["latest_game_over"] = None
                        shared_state["match_start_payload"] = None
                    spectator_mode["value"] = False
                    match_over_event.clear()
                    in_match_event.clear()
                    with challenge_lock:
                        challenge_queue.clear()
                    lobby_state.incoming_challenge_from = None
                    reset_to_lobby_surface()
                    conn.request_user_list()
                    accept_challenges.set()
                    with state_lock:
                        shared_state["chat_messages"] = []
                    phase = AppPhase.LOBBY
                elif action == "quit":
                    running = False

        if phase == AppPhase.LOGIN:
            draw_login(
                screen,
                login_state,
                title_font=title_font,
                font=font,
                small_font=small_font,
                tiny_font=tiny_font,
                mouse_pos=mouse_pos,
            )
        elif phase == AppPhase.LOBBY:
            assert conn is not None
            with state_lock:
                users = list(shared_state["latest_users"])
            draw_lobby(
                screen,
                lobby_state,
                user_entries=users,
                my_username=my_username,
                title_font=title_font,
                font=font,
                small_font=small_font,
                tiny_font=tiny_font,
                time_ms=ticks,
                mouse_pos=mouse_pos,
            )
        elif phase == AppPhase.GAME_OVER:
            with state_lock:
                go_payload = shared_state.get("latest_game_over") or {}
            draw_game_over(
                screen,
                game_over_payload=go_payload,
                title_font=title_font,
                font=font,
                small_font=small_font,
                tiny_font=tiny_font,
                mouse_pos=mouse_pos,
            )

        pygame.display.flip()
        clock.tick(60)

    cleanup_disconnect()
    pygame.quit()
