"""
shared/models.py

Core game-side data structures (Phase D).

Pure state only: no sockets, no I/O, no tick or collision logic. Networking
layers attach transport separately (see ``server.player.ConnectedPlayer``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from shared import constants as C


class Direction(str, Enum):
    """Grid movement directions (single-axis steps of one cell per tick)."""

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class PlayerStatus(str, Enum):
    """High-level presence for lobby and matchmaking (extend as needed)."""

    LOBBY = "lobby"
    IN_GAME = "in_game"
    SPECTATOR = "spectator"
    DISCONNECTED = "disconnected"


class ControlScheme(str, Enum):
    """Logical control layout; keybinding maps live on the client (Phase E+)."""

    WASD = "WASD"
    ARROWS = "ARROWS"
    # CUSTOM reserved for future UI-configurable bindings


class SnakeStyle(str, Enum):
    """Cosmetic / theme id for rendering; server echoes in STATE snapshots."""

    DEFAULT_A = "default_a"
    DEFAULT_B = "default_b"
    CYAN = "cyan"
    LIME = "lime"
    ROSE = "rose"
    AMBER = "amber"
    VIOLET = "violet"


class PieKind(str, Enum):
    """Collectible variants; spawn mix is controlled in ``constants``."""

    NORMAL = "normal"
    GOLDEN = "golden"
    POISON = "poison"
    SPEED = "speed"
    SHIELD = "shield"


class ObstacleKind(str, Enum):
    """Obstacle archetype; behavior extensions (moving hazards) are future work."""

    STATIC = "static"
    ROCK = "rock"


class GamePhase(str, Enum):
    """Match lifecycle; tick loop advances only RUNNING in a later phase."""

    PENDING = "pending"
    RUNNING = "running"
    ENDED = "ended"


@dataclass
class Player:
    """
    Player preferences and session state without any transport.

    The server maps ``username`` to a live connection (e.g. ``ConnectedPlayer``).
    """

    username: str
    status: PlayerStatus = PlayerStatus.LOBBY
    snake_style: SnakeStyle = SnakeStyle.DEFAULT_A
    control_scheme: ControlScheme = ControlScheme.WASD
    current_match_id: Optional[str] = None


@dataclass
class Snake:
    """
    One snake in a match. ``body[0]`` is the head; tail follows in play order.

    ``pending_direction`` buffers the next turn input until the server applies
    it between ticks (prevents instant 180° in one tick — logic in Phase E).
    """

    owner_username: str
    body: list[tuple[int, int]] = field(default_factory=list)
    direction: Direction = Direction.RIGHT
    pending_direction: Optional[Direction] = None
    style: SnakeStyle = SnakeStyle.DEFAULT_A
    alive: bool = True


@dataclass(frozen=True)
class Pie:
    """Collectible at a single cell; use ``create_pie`` so deltas match ``kind``."""

    id: str
    x: int
    y: int
    kind: PieKind
    delta_health: int = C.PIE_NORMAL_HEALTH_DELTA
    delta_score: int = C.PIE_NORMAL_SCORE_DELTA
# I use this function to pie health and score.


def pie_health_and_score(kind: PieKind) -> tuple[int, int]:
    """Health and score deltas applied when a snake collects this pie kind."""
    if kind == PieKind.NORMAL:
        return C.PIE_NORMAL_HEALTH_DELTA, C.PIE_NORMAL_SCORE_DELTA
    if kind == PieKind.GOLDEN:
        return C.PIE_GOLDEN_HEALTH_DELTA, C.PIE_GOLDEN_SCORE_DELTA
    if kind == PieKind.POISON:
        return C.PIE_POISON_HEALTH_DELTA, C.PIE_POISON_SCORE_DELTA
    if kind == PieKind.SPEED:
        return C.PIE_SPEED_HEALTH_DELTA, C.PIE_SPEED_SCORE_DELTA
    if kind == PieKind.SHIELD:
        return C.PIE_SHIELD_HEALTH_DELTA, C.PIE_SHIELD_SCORE_DELTA
    return C.PIE_NORMAL_HEALTH_DELTA, C.PIE_NORMAL_SCORE_DELTA
# I use this function to create pie.


def create_pie(pie_id: str, x: int, y: int, kind: PieKind) -> Pie:
    """Build a pie with authoritative effect values for its type."""
    dh, ds = pie_health_and_score(kind)
    return Pie(id=pie_id, x=x, y=y, kind=kind, delta_health=dh, delta_score=ds)


@dataclass(frozen=True)
class Obstacle:
    """Static (for now) hazard occupying one grid cell."""

    id: str
    x: int
    y: int
    kind: ObstacleKind = ObstacleKind.STATIC
    damage: int = C.OBSTACLE_DEFAULT_DAMAGE


@dataclass
class GameSession:
    """
    Authoritative match container for one head-to-head game.

    ``player_usernames`` order defines player 1 vs player 2 (spawn sides, HUD).
    ``snakes`` is keyed by the same usernames for O(1) lookup during ticks.
    """

    match_id: str
    player_usernames: tuple[str, str]
    board_width: int
    board_height: int
    snakes: dict[str, Snake]
    pies: list[Pie]
    obstacles: list[Obstacle]
    health_by_player: dict[str, int]
    time_remaining_s: float
    phase: GamePhase = GamePhase.PENDING
    tick: int = 0
    winner_username: Optional[str] = None
    score_by_player: dict[str, int] = field(default_factory=dict)
    spectators: set[str] = field(default_factory=set)
    speed_boost_ticks_by_player: dict[str, int] = field(default_factory=dict)
    shield_ticks_by_player: dict[str, int] = field(default_factory=dict)
