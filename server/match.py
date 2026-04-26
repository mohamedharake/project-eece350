"""
server/match.py

Match/session construction helpers (Phase D).

Creates a ``GameSession`` with board dimensions and timers from ``shared.constants``.
Snake bodies are placed at opposite corners as **data placeholders** only;
movement, collisions, and pie/obstacle population are later phases.
"""

from __future__ import annotations

import random
import uuid

from shared import constants as C
from shared.models import (
    Direction,
    GamePhase,
    GameSession,
    Obstacle,
    ObstacleKind,
    Pie,
    PieKind,
    Snake,
    SnakeStyle,
    create_pie,
)
# I use this function to linear body.


def _linear_body(
    head_x: int,
    head_y: int,
    length: int,
    *,
    growing: Direction,
) -> list[tuple[int, int]]:
    """
    Build a straight ``body`` list with head at (head_x, head_y).

    Tail extends opposite to ``growing`` (the direction the snake will move
    toward first tick). Coordinates are not clamped here — caller must keep
    segments inside the board when choosing corners.
    """

    opposite = {
        Direction.UP: (0, 1),
        Direction.DOWN: (0, -1),
        Direction.LEFT: (1, 0),
        Direction.RIGHT: (-1, 0),
    }
    dx, dy = opposite[growing]
    body: list[tuple[int, int]] = []
    for i in range(length):
        body.append((head_x + dx * i, head_y + dy * i))
    return body
# I use this function to default snakes for players.


def default_snakes_for_players(player_a: str, player_b: str, board_w: int, board_h: int) -> dict[str, Snake]:
    """Initial snake placement for two players (placeholder geometry)."""

    length = max(1, C.INITIAL_SNAKE_LENGTH)
    # Player A: upper-left area, facing RIGHT
    a_head = (2, 2)
    a_dir = Direction.RIGHT
    body_a = _linear_body(a_head[0], a_head[1], length, growing=a_dir)
    # Player B: lower-right area, facing LEFT
    b_head = (board_w - 3, board_h - 3)
    b_dir = Direction.LEFT
    body_b = _linear_body(b_head[0], b_head[1], length, growing=b_dir)

    return {
        player_a: Snake(
            owner_username=player_a,
            body=body_a,
            direction=a_dir,
            style=SnakeStyle.DEFAULT_A,
        ),
        player_b: Snake(
            owner_username=player_b,
            body=body_b,
            direction=b_dir,
            style=SnakeStyle.DEFAULT_B,
        ),
    }
# I use this function to snakes for players with styles.


def snakes_for_players_with_styles(
    player_a: str,
    player_b: str,
    board_w: int,
    board_h: int,
    *,
    style_by_player: dict[str, SnakeStyle] | None = None,
) -> dict[str, Snake]:
    """Initial snake placement using optional per-player style preferences."""
    snakes = default_snakes_for_players(player_a, player_b, board_w, board_h)
    if not style_by_player:
        return snakes
    if player_a in style_by_player:
        snakes[player_a].style = style_by_player[player_a]
    if player_b in style_by_player:
        snakes[player_b].style = style_by_player[player_b]
    return snakes
# I use this function to new game session.


def new_game_session(
    player_a: str,
    player_b: str,
    *,
    match_id: str | None = None,
    style_by_player: dict[str, SnakeStyle] | None = None,
) -> GameSession:
    """
    Allocate a new ``GameSession`` with default constants.

    ``pies`` and ``obstacles`` start empty; spawning passes fill them later.
    ``score_by_player`` starts at zero for both usernames.
    """

    mid = match_id or str(uuid.uuid4())
    bw, bh = C.BOARD_W, C.BOARD_H
    snakes = snakes_for_players_with_styles(player_a, player_b, bw, bh, style_by_player=style_by_player)
    return GameSession(
        match_id=mid,
        player_usernames=(player_a, player_b),
        board_width=bw,
        board_height=bh,
        snakes=snakes,
        pies=[],
        obstacles=[],
        health_by_player={player_a: C.STARTING_HEALTH, player_b: C.STARTING_HEALTH},
        time_remaining_s=float(C.GAME_DURATION_S),
        phase=GamePhase.PENDING,
        tick=0,
        winner_username=None,
        score_by_player={player_a: 0, player_b: 0},
        speed_boost_ticks_by_player={player_a: 0, player_b: 0},
        shield_ticks_by_player={player_a: 0, player_b: 0},
    )
# I use this function to in bounds.


def in_bounds(x: int, y: int, board_w: int, board_h: int) -> bool:
    """Return whether (x, y) lies inside the board rectangle [0, w) × [0, h)."""
    return 0 <= x < board_w and 0 <= y < board_h
# I use this function to occupied cells.


def occupied_cells(session: GameSession, *, include_pies: bool) -> set[tuple[int, int]]:
    """All cells blocked by snakes and obstacles; optionally include pie cells for spawning."""
    occupied: set[tuple[int, int]] = set()
    for snake in session.snakes.values():
        occupied.update(snake.body)
    for obstacle in session.obstacles:
        occupied.add((obstacle.x, obstacle.y))
    if include_pies:
        for pie in session.pies:
            occupied.add((pie.x, pie.y))
    return occupied
# I use this function to default obstacle positions.


def _default_obstacle_positions(board_w: int, board_h: int) -> list[tuple[int, int]]:
    """Deterministic obstacle placement candidates."""
    cx, cy = board_w // 2, board_h // 2
    return [
        (cx, cy),
        (cx - 1, cy),
        (cx + 1, cy),
        (cx, cy - 1),
        (cx, cy + 1),
        (board_w // 4, board_h // 3),
        ((3 * board_w) // 4, (2 * board_h) // 3),
        (board_w // 4, (2 * board_h) // 3),
        ((3 * board_w) // 4, board_h // 3),
        (board_w // 2, board_h // 4),
        (board_w // 2, (3 * board_h) // 4),
    ]
# I use this function to initialize obstacles.


def initialize_obstacles(session: GameSession, obstacle_count: int | None = None) -> None:
    """
    Fill session obstacles with deterministic positions.

    Existing obstacles are replaced.
    """
    wanted = obstacle_count if obstacle_count is not None else C.OBSTACLE_COUNT
    base_occupied = occupied_cells(session, include_pies=False)
    placed: list[Obstacle] = []
    for idx, (x, y) in enumerate(_default_obstacle_positions(session.board_width, session.board_height)):
        if len(placed) >= wanted:
            break
        if not in_bounds(x, y, session.board_width, session.board_height):
            continue
        if (x, y) in base_occupied:
            continue
        base_occupied.add((x, y))
        placed.append(Obstacle(id=f"obs-{idx}", x=x, y=y, kind=ObstacleKind.ROCK))
    session.obstacles = placed
# I use this function to random pie kind.


def _random_pie_kind() -> PieKind:
    """Weighted random pie type."""
    r = random.random()
    if r < C.PIE_SPAWN_WEIGHT_NORMAL:
        return PieKind.NORMAL
    cutoff = C.PIE_SPAWN_WEIGHT_NORMAL + C.PIE_SPAWN_WEIGHT_GOLDEN
    if r < cutoff:
        return PieKind.GOLDEN
    cutoff += C.PIE_SPAWN_WEIGHT_POISON
    if r < cutoff:
        return PieKind.POISON
    cutoff += C.PIE_SPAWN_WEIGHT_SPEED
    if r < cutoff:
        return PieKind.SPEED
    cutoff += C.PIE_SPAWN_WEIGHT_SHIELD
    if r < cutoff:
        return PieKind.SHIELD
    return PieKind.POISON
# I use this function to spawn single pie.


def spawn_single_pie(session: GameSession, pie_id: str) -> Pie | None:
    """Pick a random free board cell; type is weighted random."""
    blocked = occupied_cells(session, include_pies=True)
    kind = _random_pie_kind()
    free_cells: list[tuple[int, int]] = []
    for y in range(session.board_height):
        for x in range(session.board_width):
            if (x, y) not in blocked:
                free_cells.append((x, y))
    if free_cells:
        x, y = random.choice(free_cells)
        return create_pie(pie_id, x, y, kind)
    return None
# I use this function to initialize pies.


def initialize_pies(session: GameSession, pie_count: int | None = None) -> None:
    """
    Replace session pies with ``pie_count`` collectibles.

    Free cells are picked randomly; pie kinds are weighted random.
    """
    wanted = pie_count if pie_count is not None else C.NUM_PIES
    session.pies = []
    for idx in range(wanted):
        pie = spawn_single_pie(session, f"pie-{idx}")
        if pie is None:
            break
        session.pies.append(pie)
# I use this function to respawn pie.


def respawn_pie(session: GameSession, removed_pie_id: str) -> None:
    """Replace a consumed pie with a new one in a random available cell."""
    pie = spawn_single_pie(session, removed_pie_id)
    if pie is not None:
        session.pies.append(pie)
# I use this function to activate session.


def activate_session(session: GameSession) -> None:
    """Mark a prepared session as running."""
    session.phase = GamePhase.RUNNING
# I use this function to create running session.


def create_running_session(
    player_a: str,
    player_b: str,
    *,
    match_id: str | None = None,
    style_by_player: dict[str, SnakeStyle] | None = None,
) -> GameSession:
    """Convenience helper for Phase E match startup."""
    session = new_game_session(player_a, player_b, match_id=match_id, style_by_player=style_by_player)
    initialize_obstacles(session)
    initialize_pies(session)
    activate_session(session)
    return session
