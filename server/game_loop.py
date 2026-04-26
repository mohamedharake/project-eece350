"""
server/game_loop.py

Fixed-tick simulation for one ``GameSession``.

Each tick (see ``shared.constants.TICK_RATE``): apply buffered direction changes,
advance snakes one cell, resolve pie pickup (health/score, respawn pies), then
wall/obstacle/snake collision penalties. Snapshots are serialized via
``GameStateSnapshot`` and pushed to clients by ``net_server`` callbacks.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from server.match import in_bounds, respawn_pie
from shared import constants as C
from shared.models import Direction, GamePhase, GameSession, PieKind, Snake
from shared.types import GameStateSnapshot


@dataclass
class MatchRuntime:
    """Wraps ``GameSession`` with a lock; the match thread owns tick advancement."""

    session: GameSession
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop_requested: bool = False
    end_reason: str | None = None
# I use this function to direction vector.


def _direction_vector(direction: Direction) -> tuple[int, int]:
    """Map a facing direction to grid delta (dx, dy) for one cell step."""
    return {
        Direction.UP: (0, -1),
        Direction.DOWN: (0, 1),
        Direction.LEFT: (-1, 0),
        Direction.RIGHT: (1, 0),
    }[direction]
# I use this function to opposite direction.


def _opposite_direction(direction: Direction) -> Direction:
    """Return the direction opposite to ``direction`` (used after wall bounce)."""
    return {
        Direction.UP: Direction.DOWN,
        Direction.DOWN: Direction.UP,
        Direction.LEFT: Direction.RIGHT,
        Direction.RIGHT: Direction.LEFT,
    }[direction]
# I use this function to is reverse.


def _is_reverse(current: Direction, next_direction: Direction) -> bool:
    """True if turning from ``current`` to ``next_direction`` is a 180° reversal."""
    return (
        (current == Direction.UP and next_direction == Direction.DOWN)
        or (current == Direction.DOWN and next_direction == Direction.UP)
        or (current == Direction.LEFT and next_direction == Direction.RIGHT)
        or (current == Direction.RIGHT and next_direction == Direction.LEFT)
    )
# I use this function to queue player direction.


def queue_player_direction(runtime: MatchRuntime, username: str, direction: Direction) -> bool:
    """
    Store latest direction request for a player.

    The game loop decides when to apply it; returns False if username is not in session.
    """
    with runtime.lock:
        snake = runtime.session.snakes.get(username)
        if snake is None:
            return False
        snake.pending_direction = direction
        return True
# I use this function to apply pending direction.


def _apply_pending_direction(snake: Snake) -> None:
    """Apply buffered turn if it is not a reverse; then clear ``pending_direction``."""
    if snake.pending_direction is None:
        return
    if not _is_reverse(snake.direction, snake.pending_direction):
        snake.direction = snake.pending_direction
    snake.pending_direction = None
# I use this function to move snake head.


def _move_snake_head(snake: Snake) -> None:
    """Advance head one cell along ``snake.direction`` and drop the tail segment."""
    if not snake.alive or not snake.body:
        return
    head_x, head_y = snake.body[0]
    dx, dy = _direction_vector(snake.direction)
    new_head = (head_x + dx, head_y + dy)
    snake.body.insert(0, new_head)
    snake.body.pop()
# I use this function to apply pie collection.


def _apply_pie_collection(session: GameSession, snake: Snake) -> None:
    """Handle pies under the head: apply effects, remove pies, respawn replacements."""
    if not snake.alive or not snake.body:
        return
    head = snake.body[0]
    consumed = [pie for pie in session.pies if (pie.x, pie.y) == head]
    if not consumed:
        return
    owner = snake.owner_username
    for pie in consumed:
        delta_health = pie.delta_health
        # Shield protects against negative health effects (e.g., poison).
        if delta_health < 0 and session.shield_ticks_by_player.get(owner, 0) > 0:
            delta_health = 0
        session.health_by_player[owner] += delta_health
        session.health_by_player[owner] = max(0, session.health_by_player[owner])
        session.score_by_player[owner] += pie.delta_score
        if pie.kind == PieKind.SPEED:
            session.speed_boost_ticks_by_player[owner] = C.SPEED_BOOST_DURATION_TICKS
        elif pie.kind == PieKind.SHIELD:
            session.shield_ticks_by_player[owner] = C.SHIELD_DURATION_TICKS
        if session.health_by_player[owner] <= 0:
            snake.alive = False
    session.pies = [pie for pie in session.pies if (pie.x, pie.y) != head]
    for pie in consumed:
        respawn_pie(session, pie.id)
# I use this function to apply collision damage.


def _apply_collision_damage(session: GameSession, previous_heads: dict[str, tuple[int, int]]) -> None:
    """After movement, apply wall/body/obstacle damage; bump heads back and bounce if needed."""
    board_w = session.board_width
    board_h = session.board_height
    obstacle_cells = {(obs.x, obs.y): obs for obs in session.obstacles}
    usernames = session.player_usernames
    snake_a = session.snakes[usernames[0]]
    snake_b = session.snakes[usernames[1]]

    penalties: dict[str, int] = {usernames[0]: 0, usernames[1]: 0}
    collided: dict[str, bool] = {usernames[0]: False, usernames[1]: False}
    wall_hit: dict[str, bool] = {usernames[0]: False, usernames[1]: False}
    obstacle_hit: dict[str, bool] = {usernames[0]: False, usernames[1]: False}
    heads = {
        usernames[0]: snake_a.body[0] if snake_a.body else None,
        usernames[1]: snake_b.body[0] if snake_b.body else None,
    }

    # Walls and obstacles
    for username in usernames:
        head = heads[username]
        if head is None:
            continue
        if not in_bounds(head[0], head[1], board_w, board_h):
            penalties[username] += C.COLLISION_PENALTY_WALL
            collided[username] = True
            wall_hit[username] = True
        obstacle = obstacle_cells.get(head)
        if obstacle is not None:
            penalties[username] += max(C.COLLISION_PENALTY_OBSTACLE, obstacle.damage)
            collided[username] = True
            obstacle_hit[username] = True

    # Snake collisions (self and other snake body)
    if heads[usernames[0]] is not None and heads[usernames[1]] is not None and heads[usernames[0]] == heads[usernames[1]]:
        penalties[usernames[0]] += C.COLLISION_PENALTY_SNAKE
        penalties[usernames[1]] += C.COLLISION_PENALTY_SNAKE
        collided[usernames[0]] = True
        collided[usernames[1]] = True

    body_a_other = set(snake_a.body[1:])
    body_b_other = set(snake_b.body[1:])
    if heads[usernames[0]] in body_a_other or heads[usernames[0]] in body_b_other:
        penalties[usernames[0]] += C.COLLISION_PENALTY_SNAKE
        collided[usernames[0]] = True
    if heads[usernames[1]] in body_b_other or heads[usernames[1]] in body_a_other:
        penalties[usernames[1]] += C.COLLISION_PENALTY_SNAKE
        collided[usernames[1]] = True

    for username, damage in penalties.items():
        if damage > 0:
            effective_damage = 0 if session.shield_ticks_by_player.get(username, 0) > 0 else damage
            session.health_by_player[username] = max(0, session.health_by_player[username] - effective_damage)
            if session.health_by_player[username] <= 0:
                session.snakes[username].alive = False

    # Collision response: bump snake back to its previous valid head position.
    # This avoids repeated rapid damage from staying embedded in a wall/snake.
    for username in usernames:
        snake = session.snakes[username]
        if not collided[username] or not snake.body:
            continue
        prev_head = previous_heads.get(username)
        if prev_head is not None:
            snake.body[0] = prev_head
        if wall_hit[username] or obstacle_hit[username]:
            # Bounce off hazards so the next step goes back to a safer cell.
            snake.direction = _opposite_direction(snake.direction)
            snake.pending_direction = None
# I use this function to update end state.


def _update_end_state(session: GameSession) -> str | None:
    """If match should end, set phase/winner and return a reason token; else None."""
    p1, p2 = session.player_usernames
    h1 = session.health_by_player[p1]
    h2 = session.health_by_player[p2]
    s1 = session.score_by_player.get(p1, 0)
    s2 = session.score_by_player.get(p2, 0)
    if h1 <= 0 and h2 <= 0:
        session.phase = GamePhase.ENDED
        session.winner_username = None
        return "both_depleted"
    if h1 <= 0:
        session.phase = GamePhase.ENDED
        session.winner_username = p2
        return "health_depleted"
    if h2 <= 0:
        session.phase = GamePhase.ENDED
        session.winner_username = p1
        return "health_depleted"
    if session.time_remaining_s <= 0:
        session.phase = GamePhase.ENDED
        if s1 > s2:
            session.winner_username = p1
        elif s2 > s1:
            session.winner_username = p2
        else:
            session.winner_username = None
        return "timer_expired"
    return None
# I use this function to tick down effects.


def _tick_down_effects(session: GameSession) -> None:
    """Reduce active temporary effects by one tick."""
    for username in session.player_usernames:
        session.speed_boost_ticks_by_player[username] = max(
            0,
            session.speed_boost_ticks_by_player.get(username, 0) - 1,
        )
        session.shield_ticks_by_player[username] = max(
            0,
            session.shield_ticks_by_player.get(username, 0) - 1,
        )
# I use this function to tick once.


def _tick_once(runtime: MatchRuntime, tick_dt_s: float) -> str | None:
    """Advance simulation by one tick: move, pies, optional speed move, collisions, timer."""
    session = runtime.session
    if session.phase != GamePhase.RUNNING:
        return "not_running"

    previous_heads = {
        username: session.snakes[username].body[0]
        for username in session.player_usernames
        if session.snakes[username].body
    }
    for username in session.player_usernames:
        _apply_pending_direction(session.snakes[username])
    for username in session.player_usernames:
        _move_snake_head(session.snakes[username])
    for username in session.player_usernames:
        _apply_pie_collection(session, session.snakes[username])
    # Speed boost grants one additional cell move per tick.
    for username in session.player_usernames:
        if session.speed_boost_ticks_by_player.get(username, 0) > 0:
            _move_snake_head(session.snakes[username])
            _apply_pie_collection(session, session.snakes[username])

    _apply_collision_damage(session, previous_heads)
    _tick_down_effects(session)

    session.tick += 1
    session.time_remaining_s = max(0.0, session.time_remaining_s - tick_dt_s)
    return _update_end_state(session)
# I use this function to run match loop.


def run_match_loop(
    runtime: MatchRuntime,
    *,
    on_state: Callable[[dict], None],
    on_game_over: Callable[[dict], None],
) -> None:
    """
    Run until the match ends or ``stop_requested`` is set.

    Invokes ``on_state`` every tick with a wire-format dict; ``on_game_over``
    once with final state plus end ``reason``. Serialized dicts match
    ``GameStateSnapshot.to_wire_dict()`` shape.
    """
    tick_dt = 1.0 / max(1, C.TICK_RATE)

    # Small pre-game delay to give clients time to switch from
    # console lobby into their Pygame windows before movement starts.
    time.sleep(3.0)

    while True:
        tick_start = time.monotonic()
        with runtime.lock:
            if runtime.stop_requested:
                runtime.session.phase = GamePhase.ENDED
                runtime.end_reason = runtime.end_reason or "aborted"
                snapshot = GameStateSnapshot.from_session(runtime.session)
                final_payload = snapshot.to_wire_dict()
                final_payload["reason"] = runtime.end_reason
                on_game_over(final_payload)
                break

            end_reason = _tick_once(runtime, tick_dt)
            snapshot = GameStateSnapshot.from_session(runtime.session)
            state_payload = snapshot.to_wire_dict()
            on_state(state_payload)
            if end_reason is not None and runtime.session.phase == GamePhase.ENDED:
                final_payload = dict(state_payload)
                final_payload["reason"] = end_reason
                on_game_over(final_payload)
                break

        elapsed = time.monotonic() - tick_start
        sleep_s = tick_dt - elapsed
        if sleep_s > 0:
            time.sleep(sleep_s)
