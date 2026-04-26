"""
client/net_client.py

Client-side TCP wrapper for NDJSON protocol messages.

``ClientConnection`` exposes small methods used by ``client.main`` (registration,
lobby, moves, chat, spectate) and a blocking ``receive_forever`` helper for the
background receiver thread during play.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Any, Callable

from shared.protocol import (
    MSG_CHALLENGE_REQUEST,
    MSG_CHALLENGE_RESPONSE,
    MSG_GET_USERS,
    MSG_MOVE,
    MSG_CHAT_SEND,
    MSG_WATCH_REQUEST,
    MSG_REGISTER,
    MSG_REGISTER_ERROR,
    MSG_REGISTER_OK,
    PROTOCOL_VERSION,
)
from shared.serialize import recv_json_line, send_json


@dataclass
class ClientConnection:
    """Stateful TCP connection: send helpers + line-oriented JSON receive."""

    sock: socket.socket
    file_obj: Any

    # I use this function to connect.
    @classmethod
    def connect(cls, host: str, port: int) -> "ClientConnection":
        """Open a TCP connection and a binary readline wrapper for NDJSON receive."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        return cls(sock=sock, file_obj=sock.makefile("rb"))
    # I use this function to close.

    def close(self) -> None:
        """Shutdown and close the socket and file object so ``receive_forever`` unblocks."""
        # Unblock any thread waiting in recv/readline before close.
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.file_obj.close()
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
    # I use this function to register username.

    def register_username(
        self,
        username: str,
        *,
        snake_style: str = "default_a",
        control_scheme: str = "ARROWS",
    ) -> tuple[bool, str]:
        """Send ``REGISTER`` and wait for ok/error; returns (success, username or error detail)."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_REGISTER,
                "payload": {
                    "username": username,
                    "snake_style": snake_style,
                    "control_scheme": control_scheme,
                },
            },
        )

        response = recv_json_line(self.file_obj)
        if response is None:
            return False, "No response from server."

        msg_type = response.get("type")
        payload = response.get("payload", {})
        if msg_type == MSG_REGISTER_OK:
            return True, payload.get("username", username)
        if msg_type == MSG_REGISTER_ERROR:
            return False, payload.get("detail", "Registration failed.")
        return False, f"Unexpected response type: {msg_type}"
    # I use this function to request user list.

    def request_user_list(self) -> None:
        """Ask the server to broadcast (and we will get) an updated user list message."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_GET_USERS,
                "payload": {},
            },
        )
    # I use this function to send challenge request.

    def send_challenge_request(self, target_username: str) -> None:
        """Send a challenge to ``target_username`` (server forwards to that client)."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_CHALLENGE_REQUEST,
                "payload": {"to": target_username},
            },
        )
    # I use this function to send challenge response.

    def send_challenge_response(self, challenger_username: str, accepted: bool) -> None:
        """Accept or decline a pending challenge from ``challenger_username``."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_CHALLENGE_RESPONSE,
                "payload": {"to": challenger_username, "accepted": accepted},
            },
        )
    # I use this function to send move.

    def send_move(self, direction: str) -> None:
        """Queue a movement direction (UP/DOWN/LEFT/RIGHT) for the active match."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_MOVE,
                "payload": {"direction": direction},
            },
        )
    # I use this function to send chat.

    def send_chat(self, text: str) -> None:
        """Send ``CHAT_SEND`` with the given line (server fans out to match + spectators)."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_CHAT_SEND,
                "payload": {"text": text},
            },
        )
    # I use this function to send watch request.

    def send_watch_request(self) -> None:
        """Request spectate access; server replies with watch ok/error and match id."""
        send_json(
            self.sock,
            {
                "v": PROTOCOL_VERSION,
                "type": MSG_WATCH_REQUEST,
                "payload": {},
            },
        )
    # I use this function to receive forever.

    def receive_forever(self, on_message: Callable[[dict[str, Any]], None]) -> None:
        """Read messages until EOF; invoke ``on_message`` for each parsed JSON object."""
        while True:
            message = recv_json_line(self.file_obj)
            if message is None:
                break
            on_message(message)

