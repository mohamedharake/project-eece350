"""
shared/constants.py

Central tunable game + protocol constants (Phase D).

Server should treat gameplay-impacting values as authoritative; clients use
these for defaults and local prediction only where applicable later.
"""

from __future__ import annotations

from typing import Final

# --- Board (grid cells) -------------------------------------------------
BOARD_W: Final[int] = 40
BOARD_H: Final[int] = 30

# --- Client rendering (pixels per cell; not used server-side yet) -----
CELL_SIZE_PX: Final[int] = 20

# --- Simulation timing --------------------------------------------------
TICK_RATE: Final[int] = 12  # server ticks per second (target)
GAME_DURATION_S: Final[int] = 120

# --- Health / scoring ----------------------------------------------------
STARTING_HEALTH: Final[int] = 10

# Pie effects (spawn uses ``create_pie`` in models for consistent deltas)
PIE_NORMAL_HEALTH_DELTA: Final[int] = 1
PIE_NORMAL_SCORE_DELTA: Final[int] = 0
PIE_GOLDEN_HEALTH_DELTA: Final[int] = 4
PIE_GOLDEN_SCORE_DELTA: Final[int] = 5
PIE_POISON_HEALTH_DELTA: Final[int] = -3
PIE_POISON_SCORE_DELTA: Final[int] = 0
PIE_SPEED_HEALTH_DELTA: Final[int] = 0
PIE_SPEED_SCORE_DELTA: Final[int] = 1
PIE_SHIELD_HEALTH_DELTA: Final[int] = 0
PIE_SHIELD_SCORE_DELTA: Final[int] = 1

# Random pie type weights (must sum to 1.0)
PIE_SPAWN_WEIGHT_NORMAL: Final[float] = 0.42
PIE_SPAWN_WEIGHT_GOLDEN: Final[float] = 0.20
PIE_SPAWN_WEIGHT_POISON: Final[float] = 0.18
PIE_SPAWN_WEIGHT_SPEED: Final[float] = 0.10
PIE_SPAWN_WEIGHT_SHIELD: Final[float] = 0.10

# Temporary effect durations (in ticks).
SPEED_BOOST_DURATION_TICKS: Final[int] = 5 * TICK_RATE
SHIELD_DURATION_TICKS: Final[int] = 5 * TICK_RATE

# Collision / hazard (used when applying damage in a later phase)
COLLISION_PENALTY_WALL: Final[int] = 1
COLLISION_PENALTY_OBSTACLE: Final[int] = 2
COLLISION_PENALTY_SNAKE: Final[int] = 1
OBSTACLE_DEFAULT_DAMAGE: Final[int] = 1

# --- Spawning (initial counts; respawn logic comes later) ---------------
NUM_PIES: Final[int] = 5
OBSTACLE_COUNT: Final[int] = 8

# Initial snake length (head + tail segments to place on match start)
INITIAL_SNAKE_LENGTH: Final[int] = 3

# --- Accounts / protocol -------------------------------------------------
MAX_USERNAME_LEN: Final[int] = 16
MAX_LINE_BYTES: Final[int] = 64 * 1024  # defensive cap for NDJSON lines

# --- Directions (string tokens; must match ``Direction`` enum values) --
CANONICAL_DIRECTIONS: Final[tuple[str, ...]] = ("UP", "DOWN", "LEFT", "RIGHT")
