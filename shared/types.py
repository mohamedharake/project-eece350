"""
shared/types.py

Wire-friendly / snapshot shapes used by protocol and UI layers (Phase D).

Core gameplay types live in ``shared.models``; this module re-exports the
common ones for convenience and defines DTOs that are not full ``GameSession``
containers (e.g. compact STATE payloads later).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.models import (
    ControlScheme,
    Direction,
    GamePhase,
    GameSession,
    Obstacle,
    ObstacleKind,
    Pie,
    PieKind,
    Player,
    PlayerStatus,
    Snake,
    SnakeStyle,
)

# Re-export model symbols for callers that used ``shared.types`` historically.
__all__ = [
    "ControlScheme",
    "Direction",
    "GamePhase",
    "GameSession",
    "Obstacle",
    "ObstacleKind",
    "Pie",
    "PieKind",
    "Player",
    "PlayerPublic",
    "PlayerStatus",
    "Snake",
    "SnakeStyle",
    "GameStateSnapshot",
]


@dataclass
class PlayerPublic:
    """
    Minimal player record suitable for lobby lists and broadcasts.

    ``user_id`` is kept for older call sites; for this project it mirrors
    ``username`` until a separate account id exists.
    """

    user_id: str
    username: str
    status: str

    # I use this function to from player.
    @classmethod
    def from_player(cls, player: Player) -> PlayerPublic:
        """Build a public lobby row from a full ``Player`` model (ids mirror username)."""
        return cls(
            user_id=player.username,
            username=player.username,
            status=player.status.value,
        )


@dataclass
class GameStateSnapshot:
    """
    Authoritative view of the arena at one tick (client read-only).

    This is a flattened subset of ``GameSession`` for efficient STATE messages.
    """

    match_id: str
    tick: int
    board_width: int
    board_height: int
    players: tuple[str, str]
    snakes: list[Snake]
    pies: list[Pie]
    obstacles: list[Obstacle]
    time_left_s: int
    health_by_player: dict[str, int] = field(default_factory=dict)
    score_by_player: dict[str, int] = field(default_factory=dict)
    phase: GamePhase = GamePhase.RUNNING
    winner_username: str | None = None

    # I use this function to from session.
    @classmethod
    def from_session(cls, session: GameSession) -> GameStateSnapshot:
        """Flatten live ``GameSession`` into a tick snapshot for wire encoding."""
        return cls(
            match_id=session.match_id,
            tick=session.tick,
            board_width=session.board_width,
            board_height=session.board_height,
            players=session.player_usernames,
            snakes=list(session.snakes.values()),
            pies=list(session.pies),
            obstacles=list(session.obstacles),
            time_left_s=int(session.time_remaining_s),
            health_by_player=dict(session.health_by_player),
            score_by_player=dict(session.score_by_player),
            phase=session.phase,
            winner_username=session.winner_username,
        )
    # I use this function to to wire dict.

    def to_wire_dict(self) -> dict[str, Any]:
        """
        Build the JSON-shaped ``game_state`` / ``game_over`` payload for clients.

        Nested helpers convert each model type to plain dicts/lists.
        """
        # I use this function to snake dict.

        def snake_dict(s: Snake) -> dict[str, Any]:
            """Serialize one snake (body points, facing, style) for the wire format."""
            return {
                "owner": s.owner_username,
                "body": [{"x": x, "y": y} for x, y in s.body],
                "direction": s.direction.value,
                "pending": s.pending_direction.value if s.pending_direction else None,
                "style": s.style.value,
                "alive": s.alive,
            }
        # I use this function to pie dict.

        def pie_dict(p: Pie) -> dict[str, Any]:
            """Serialize one pie (position, kind, effect deltas)."""
            return {
                "id": p.id,
                "x": p.x,
                "y": p.y,
                "kind": p.kind.value,
                "delta_health": p.delta_health,
                "delta_score": p.delta_score,
            }
        # I use this function to obs dict.

        def obs_dict(o: Obstacle) -> dict[str, Any]:
            """Serialize one obstacle cell (position, kind, damage)."""
            return {
                "id": o.id,
                "x": o.x,
                "y": o.y,
                "kind": o.kind.value,
                "damage": o.damage,
            }

        return {
            "match_id": self.match_id,
            "tick": self.tick,
            "board": {"width": self.board_width, "height": self.board_height},
            "players": list(self.players),
            "snakes": [snake_dict(s) for s in self.snakes],
            "pies": [pie_dict(p) for p in self.pies],
            "obstacles": [obs_dict(o) for o in self.obstacles],
            "time_left_s": self.time_left_s,
            "health_by_player": self.health_by_player,
            "score_by_player": self.score_by_player,
            "phase": self.phase.value,
            "winner_username": self.winner_username,
        }
