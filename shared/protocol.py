"""
shared/protocol.py

Canonical message ``type`` strings for JSON-over-TCP (NDJSON).

Application code imports these constants instead of scattering string literals.
``PROTOCOL_VERSION`` is carried in each message under key ``v`` for forward
compatibility. Legacy aliases remain for older planning docs but preferred
names are used in active code paths (e.g. ``MSG_WATCH_*`` for spectating).
"""

from __future__ import annotations

from typing import Final

PROTOCOL_VERSION: Final[int] = 1

# Phase B
MSG_REGISTER: Final[str] = "REGISTER"
MSG_REGISTER_OK: Final[str] = "REGISTER_OK"
MSG_REGISTER_ERROR: Final[str] = "REGISTER_ERROR"

# Phase C (lobby + challenge)
MSG_GET_USERS: Final[str] = "get_users"
MSG_USER_LIST: Final[str] = "user_list"

MSG_CHALLENGE_REQUEST: Final[str] = "challenge_request"
MSG_CHALLENGE_RESPONSE: Final[str] = "challenge_response"

MSG_MATCH_START: Final[str] = "match_start"

# Common errors/results
MSG_ERROR: Final[str] = "error"

# Legacy names kept for compatibility with earlier planning docs
MSG_LIST_USERS: Final[str] = "LIST_USERS"
MSG_USERS: Final[str] = "USERS"
MSG_CHALLENGE: Final[str] = "CHALLENGE"
MSG_CHALLENGE_RECEIVED: Final[str] = "CHALLENGE_RECEIVED"
MSG_MATCHMAKING_ERROR: Final[str] = "MATCHMAKING_ERROR"

# Phase E (server-authoritative gameplay)
MSG_MOVE: Final[str] = "move"
MSG_GAME_STATE: Final[str] = "game_state"
MSG_GAME_OVER: Final[str] = "game_over"

# Legacy placeholders kept for compatibility with earlier planning docs
MSG_INPUT: Final[str] = "INPUT"
MSG_STATE: Final[str] = "STATE"

MSG_DISCONNECT: Final[str] = "DISCONNECT"
MSG_USER_LEFT: Final[str] = "USER_LEFT"
MSG_MATCH_ABORTED: Final[str] = "MATCH_ABORTED"

# Placeholders for later phases
MSG_CHAT_SEND: Final[str] = "CHAT_SEND"
MSG_CHAT_RECV: Final[str] = "CHAT_RECV"
MSG_SPECTATE_REQUEST: Final[str] = "SPECTATE_REQUEST"
MSG_SPECTATE_OK: Final[str] = "SPECTATE_OK"
MSG_SPECTATE_DENY: Final[str] = "SPECTATE_DENY"

# Phase I aliases (preferred semantic names)
MSG_WATCH_REQUEST: Final[str] = MSG_SPECTATE_REQUEST
MSG_WATCH_OK: Final[str] = MSG_SPECTATE_OK
MSG_WATCH_ERROR: Final[str] = MSG_SPECTATE_DENY

