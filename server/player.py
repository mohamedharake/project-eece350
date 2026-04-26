"""
server/player.py

Transport-attached player record (Phase D).

``shared.models.Player`` holds game-facing fields only; this wrapper pairs a
live TCP socket with that profile for the networking layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import socket

from shared.models import Player


@dataclass
class ConnectedPlayer:
    """
    One registered client: socket + authoritative ``Player`` profile.

    ``profile`` is mutated in place (status, ``current_match_id``, etc.) as
    the lobby and match manager evolve; the socket is owned by ``net_server``.
    """

    sock: socket.socket
    profile: Player = field(repr=False)

    # I use this function to username.
    @property
    def username(self) -> str:
        """Convenience alias for ``profile.username``."""
        return self.profile.username
