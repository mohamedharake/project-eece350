"""
server/net_server.py

Networking entry point for Python Arena.

Per-client TCP connections are handled in threads. Each peer speaks a simple
protocol: newline-delimited JSON ("NDJSON"), one logical message per line.

Responsibilities:
  - Registration and unique usernames
  - Lobby commands (user list, challenges, match start)
  - Routing ``move`` input to the authoritative ``game_loop``
  - Broadcasting ``game_state`` / ``game_over`` snapshots to players (and chat)
  - Spectator ``watch`` requests for the active match

Shared state lives in ``ServerState`` (users, active matches, quick lookups).
"""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from typing import Any

from shared.constants import MAX_USERNAME_LEN
from shared.models import ControlScheme, Direction, SnakeStyle
from shared.protocol import (
    MSG_CHALLENGE_REQUEST,
    MSG_CHALLENGE_RESPONSE,
    MSG_ERROR,
    MSG_GAME_OVER,
    MSG_GAME_STATE,
    MSG_GET_USERS,
    MSG_MATCH_START,
    MSG_MOVE,
    MSG_CHAT_SEND,
    MSG_CHAT_RECV,
    MSG_WATCH_REQUEST,
    MSG_WATCH_OK,
    MSG_WATCH_ERROR,
    MSG_REGISTER,
    MSG_REGISTER_ERROR,
    MSG_REGISTER_OK,
    MSG_USER_LIST,
    PROTOCOL_VERSION,
)
from server.game_loop import MatchRuntime, queue_player_direction, run_match_loop
from server.match import create_running_session
from shared.serialize import recv_json_line, send_json


@dataclass
class ClientInfo:
    """Live connection metadata for one registered username."""

    sock: socket.socket
    status: str = "online"  # online | in_game | spectator
    spectating_match_id: str | None = None
    snake_style: SnakeStyle = SnakeStyle.DEFAULT_A
    control_scheme: ControlScheme = ControlScheme.ARROWS


@dataclass
class ServerState:
    """
    Global server state for Phase C.
    Keeps username -> client info mapping and synchronizes access with a lock.
    """

    users: dict[str, ClientInfo] = field(default_factory=dict)
    matches: dict[str, MatchRuntime] = field(default_factory=dict)
    user_to_match: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
# I use this function to valid username.


def _valid_username(username: Any) -> bool:
    """True if ``username`` is a non-empty trimmed string within max length."""
    if not isinstance(username, str):
        return False
    trimmed = username.strip()
    return bool(trimmed) and len(trimmed) <= MAX_USERNAME_LEN
# I use this function to send error.


def _send_error(sock: socket.socket, reason: str, detail: str) -> None:
    """Send a protocol ``error`` message with the given reason and detail text."""
    send_json(
        sock,
        {
            "v": PROTOCOL_VERSION,
            "type": MSG_ERROR,
            "payload": {"reason": reason, "detail": detail},
        },
    )
# I use this function to safe send.


def _safe_send(sock: socket.socket, message: dict[str, Any]) -> None:
    """Send JSON to a socket; swallow OSError so broadcast paths do not crash."""
    try:
        send_json(sock, message)
    except OSError:
        pass
# I use this function to build user list payload.


def _build_user_list_payload(state: ServerState) -> dict[str, Any]:
    """Build the ``users`` array payload (username + status) sorted by name."""
    users_payload: list[dict[str, str]] = []
    for username, info in sorted(state.users.items()):
        users_payload.append({"username": username, "status": info.status})
    return {"users": users_payload}
# I use this function to broadcast user list.


def _broadcast_user_list(state: ServerState) -> None:
    """Push an up-to-date ``user_list`` message to every connected client."""
    with state.lock:
        recipients = [info.sock for info in state.users.values()]
        payload = _build_user_list_payload(state)

    message = {"v": PROTOCOL_VERSION, "type": MSG_USER_LIST, "payload": payload}
    for sock in recipients:
        _safe_send(sock, message)
# I use this function to send user list to.


def _send_user_list_to(sock: socket.socket, state: ServerState) -> None:
    """Send a single ``user_list`` snapshot to one socket (e.g. after ``get_users``)."""
    with state.lock:
        payload = _build_user_list_payload(state)
    send_json(sock, {"v": PROTOCOL_VERSION, "type": MSG_USER_LIST, "payload": payload})
# I use this function to broadcast to match.


def _broadcast_to_match(state: ServerState, match_id: str, message_type: str, payload: dict[str, Any]) -> None:
    """Send a typed message to both players and all spectators of the given match."""
    with state.lock:
        runtime = state.matches.get(match_id)
        if runtime is None:
            return
        recipients = set(runtime.session.player_usernames)
        recipients.update(runtime.session.spectators)
        sockets = [state.users[name].sock for name in recipients if name in state.users]
    message = {"v": PROTOCOL_VERSION, "type": message_type, "payload": payload}
    for sock in sockets:
        _safe_send(sock, message)
# I use this function to finish match.


def _finish_match(state: ServerState, match_id: str) -> None:
    """Remove the match from state, reset player/spectator statuses, rebroadcast lobby list."""
    with state.lock:
        runtime = state.matches.pop(match_id, None)
        if runtime is None:
            return
        for username in runtime.session.player_usernames:
            state.user_to_match.pop(username, None)
            info = state.users.get(username)
            if info is not None:
                info.status = "online"
                info.spectating_match_id = None
        for username in runtime.session.spectators:
            info = state.users.get(username)
            if info is not None and info.spectating_match_id == match_id:
                info.status = "online"
                info.spectating_match_id = None
    _broadcast_user_list(state)
# I use this function to start match.


def _start_match(state: ServerState, player_a: str, player_b: str) -> str:
    """Create a running session, register it, and start the match loop thread; return match id."""
    with state.lock:
        style_by_player: dict[str, SnakeStyle] = {}
        info_a = state.users.get(player_a)
        info_b = state.users.get(player_b)
        if info_a is not None:
            style_by_player[player_a] = info_a.snake_style
        if info_b is not None:
            style_by_player[player_b] = info_b.snake_style
    session = create_running_session(player_a, player_b, style_by_player=style_by_player)
    runtime = MatchRuntime(session=session)
    with state.lock:
        state.matches[session.match_id] = runtime
        state.user_to_match[player_a] = session.match_id
        state.user_to_match[player_b] = session.match_id
        if player_a in state.users:
            state.users[player_a].status = "in_game"
        if player_b in state.users:
            state.users[player_b].status = "in_game"
    # I use this function to on state.

    def on_state(payload: dict[str, Any]) -> None:
        """Hook: each tick, fan out ``game_state`` to everyone in this match."""
        _broadcast_to_match(state, session.match_id, MSG_GAME_STATE, payload)
    # I use this function to on game over.

    def on_game_over(payload: dict[str, Any]) -> None:
        """Hook: final tick; send ``game_over`` then tear down match state."""
        _broadcast_to_match(state, session.match_id, MSG_GAME_OVER, payload)
        _finish_match(state, session.match_id)

    threading.Thread(
        target=run_match_loop,
        kwargs={"runtime": runtime, "on_state": on_state, "on_game_over": on_game_over},
        daemon=True,
    ).start()
    return session.match_id
# I use this function to handle client.


def handle_client(client_sock: socket.socket, client_addr: tuple[str, int], state: ServerState) -> None:
    """
    Serve one TCP client until disconnect.

    The first message must be ``REGISTER``. After a successful registration,
    the same socket is used for lobby commands, match input (``move``), chat,
    and spectator requests until the peer closes the connection or an error
    occurs.
    """
    username: str | None = None
    file_obj = client_sock.makefile("rb")
    try:
        first_message = recv_json_line(file_obj)
        if first_message is None:
            return

        if first_message.get("type") != MSG_REGISTER:
            send_json(
                client_sock,
                {
                    "v": PROTOCOL_VERSION,
                    "type": MSG_REGISTER_ERROR,
                    "payload": {"reason": "EXPECTED_REGISTER", "detail": "First message must be REGISTER."},
                },
            )
            return

        first_payload = first_message.get("payload", {})
        requested_username = first_payload.get("username")
        if not _valid_username(requested_username):
            send_json(
                client_sock,
                {
                    "v": PROTOCOL_VERSION,
                    "type": MSG_REGISTER_ERROR,
                    "payload": {
                        "reason": "INVALID_USERNAME",
                        "detail": f"Username must be 1..{MAX_USERNAME_LEN} characters.",
                    },
                },
            )
            return

        username = requested_username.strip()
        requested_style_raw = first_payload.get("snake_style", SnakeStyle.DEFAULT_A.value)
        requested_controls_raw = first_payload.get("control_scheme", ControlScheme.ARROWS.value)
        try:
            requested_style = SnakeStyle(str(requested_style_raw).lower())
        except ValueError:
            requested_style = SnakeStyle.DEFAULT_A
        try:
            requested_controls = ControlScheme(str(requested_controls_raw).upper())
        except ValueError:
            requested_controls = ControlScheme.ARROWS
        with state.lock:
            if username in state.users:
                send_json(
                    client_sock,
                    {
                        "v": PROTOCOL_VERSION,
                        "type": MSG_REGISTER_ERROR,
                        "payload": {"reason": "USERNAME_TAKEN", "detail": "Username already in use."},
                    },
                )
                return
            state.users[username] = ClientInfo(
                sock=client_sock,
                status="online",
                snake_style=requested_style,
                control_scheme=requested_controls,
            )

        send_json(
            client_sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_REGISTER_OK,
                "payload": {
                    "username": username,
                    "snake_style": requested_style.value,
                    "control_scheme": requested_controls.value,
                },
            },
        )
        print(f"[+] Registered '{username}' from {client_addr[0]}:{client_addr[1]}")
        _broadcast_user_list(state)

        # Keep connection alive until client disconnects.
        while True:
            message = recv_json_line(file_obj)
            if message is None:
                break

            msg_type = message.get("type")
            payload = message.get("payload", {})

            if msg_type == MSG_GET_USERS:
                _send_user_list_to(client_sock, state)
                continue

            if msg_type == MSG_WATCH_REQUEST:
                if username is None:
                    _send_error(client_sock, "INVALID_ACTION", "Not registered.")
                    continue
                with state.lock:
                    user_info = state.users.get(username)
                    if user_info is None:
                        continue
                    if user_info.status == "in_game":
                        _safe_send(
                            client_sock,
                            {
                                "v": PROTOCOL_VERSION,
                                "type": MSG_WATCH_ERROR,
                                "payload": {"detail": "Players in a match cannot spectate."},
                            },
                        )
                        continue
                    running_match: MatchRuntime | None = None
                    for rt in state.matches.values():
                        if rt.session.phase.value == "running":
                            running_match = rt
                            break
                    if running_match is None:
                        _safe_send(
                            client_sock,
                            {
                                "v": PROTOCOL_VERSION,
                                "type": MSG_WATCH_ERROR,
                                "payload": {"detail": "No active match to watch right now."},
                            },
                        )
                        continue
                    running_match.session.spectators.add(username)
                    user_info.status = "spectator"
                    user_info.spectating_match_id = running_match.session.match_id
                    match_id = running_match.session.match_id
                    players = list(running_match.session.player_usernames)
                _safe_send(
                    client_sock,
                    {
                        "v": PROTOCOL_VERSION,
                        "type": MSG_WATCH_OK,
                        "payload": {"match_id": match_id, "players": players},
                    },
                )
                _broadcast_user_list(state)
                continue

            if msg_type == MSG_CHAT_SEND:
                if username is None:
                    _send_error(client_sock, "INVALID_ACTION", "Not registered.")
                    continue
                text = payload.get("text")
                if not isinstance(text, str):
                    _send_error(client_sock, "INVALID_PAYLOAD", "chat_send requires 'text' string.")
                    continue
                text = text.strip()
                if not text:
                    continue  # ignore empty
                if len(text) > 256:
                    text = text[:256]
                with state.lock:
                    user_info = state.users.get(username)
                    match_id = state.user_to_match.get(username)
                    if not match_id and user_info is not None:
                        match_id = user_info.spectating_match_id
                    runtime = state.matches.get(match_id) if match_id else None
                    if runtime is None:
                        _send_error(client_sock, "INVALID_ACTION", "You can only chat while in a live match or while spectating.")
                        continue
                    recipients = set(runtime.session.player_usernames)
                    recipients.update(runtime.session.spectators)
                    sockets = [state.users[name].sock for name in recipients if name in state.users]
                    sender_name = username
                    if user_info is not None and user_info.status == "spectator":
                        sender_name = f"[SPEC] {username}"
                chat_payload = {
                    "from": sender_name,
                    "text": text,
                }
                message_out = {"v": PROTOCOL_VERSION, "type": MSG_CHAT_RECV, "payload": chat_payload}
                for sock in sockets:
                    _safe_send(sock, message_out)
                continue

            if msg_type == MSG_MOVE:
                direction_raw = payload.get("direction")
                if not isinstance(direction_raw, str):
                    _send_error(client_sock, "INVALID_PAYLOAD", "move requires 'direction'.")
                    continue
                try:
                    direction = Direction(direction_raw.upper())
                except ValueError:
                    _send_error(client_sock, "INVALID_DIRECTION", "Direction must be UP/DOWN/LEFT/RIGHT.")
                    continue
                with state.lock:
                    match_id = state.user_to_match.get(username or "")
                    runtime = state.matches.get(match_id) if match_id else None
                if runtime is None:
                    _send_error(client_sock, "INVALID_ACTION", "You are not in an active match.")
                    continue
                if (username or "") not in runtime.session.player_usernames:
                    _send_error(client_sock, "INVALID_ACTION", "Spectators cannot send movement.")
                    continue
                queue_player_direction(runtime, username or "", direction)
                continue

            if msg_type == MSG_CHALLENGE_REQUEST:
                target_username = payload.get("to")
                if not isinstance(target_username, str):
                    _send_error(client_sock, "INVALID_PAYLOAD", "challenge_request requires 'to'.")
                    continue
                if target_username == username:
                    _send_error(client_sock, "INVALID_ACTION", "You cannot challenge yourself.")
                    continue

                with state.lock:
                    challenger = state.users.get(username)
                    target = state.users.get(target_username)
                    if challenger is None:
                        continue
                    if challenger.status != "online":
                        _send_error(client_sock, "INVALID_ACTION", "Only online users can challenge.")
                        continue
                    if target is None:
                        _send_error(client_sock, "USER_NOT_FOUND", f"User '{target_username}' is not online.")
                        continue
                    if target.status != "online":
                        _send_error(client_sock, "TARGET_BUSY", f"User '{target_username}' is busy.")
                        continue
                    target_sock = target.sock

                send_json(
                    target_sock,
                    {
                        "v": PROTOCOL_VERSION,
                        "type": MSG_CHALLENGE_REQUEST,
                        "payload": {"from": username},
                    },
                )
                continue

            if msg_type == MSG_CHALLENGE_RESPONSE:
                from_username = payload.get("to")
                accepted = bool(payload.get("accepted", False))
                if not isinstance(from_username, str):
                    _send_error(client_sock, "INVALID_PAYLOAD", "challenge_response requires 'to'.")
                    continue

                with state.lock:
                    responder = state.users.get(username)
                    challenger = state.users.get(from_username)
                    if responder is None:
                        continue
                    if responder.status != "online":
                        _send_error(client_sock, "INVALID_ACTION", "Only online users can accept challenges.")
                        continue
                    if challenger is None:
                        _send_error(client_sock, "USER_NOT_FOUND", f"User '{from_username}' is not online.")
                        continue
                    if challenger.status != "online":
                        _send_error(client_sock, "INVALID_ACTION", "Challenger is no longer available.")
                        continue

                    challenger_sock = challenger.sock
                    responder_sock = responder.sock

                    if accepted:
                        responder.status = "in_game"
                        challenger.status = "in_game"

                if accepted:
                    if username is None:
                        continue
                    started_match_id = _start_match(state, from_username, username)
                    _safe_send(
                        challenger_sock,
                        {
                            "v": PROTOCOL_VERSION,
                            "type": MSG_MATCH_START,
                            "payload": {"opponent": username, "match_id": started_match_id},
                        },
                    )
                    _safe_send(
                        responder_sock,
                        {
                            "v": PROTOCOL_VERSION,
                            "type": MSG_MATCH_START,
                            "payload": {"opponent": from_username, "match_id": started_match_id},
                        },
                    )
                    _broadcast_user_list(state)
                else:
                    send_json(
                        challenger_sock,
                        {
                            "v": PROTOCOL_VERSION,
                            "type": MSG_CHALLENGE_RESPONSE,
                            "payload": {"from": username, "accepted": False},
                        },
                    )
                continue
    except (ConnectionError, OSError, ValueError):
        pass
    finally:
        file_obj.close()
        match_to_abort: str | None = None
        with state.lock:
            if username and username in state.users and state.users[username].sock is client_sock:
                match_to_abort = state.user_to_match.get(username)
                spectating_match_id = state.users[username].spectating_match_id
                if spectating_match_id:
                    runtime = state.matches.get(spectating_match_id)
                    if runtime is not None:
                        runtime.session.spectators.discard(username)
                del state.users[username]
                print(f"[-] Disconnected '{username}'. Active users: {len(state.users)}")
        client_sock.close()
        if match_to_abort:
            with state.lock:
                runtime = state.matches.get(match_to_abort)
            if runtime is not None:
                with runtime.lock:
                    runtime.stop_requested = True
                    runtime.end_reason = "player_disconnected"
        _broadcast_user_list(state)

