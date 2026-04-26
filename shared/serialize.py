"""
shared/serialize.py

Framing layer for the wire protocol: each logical message is one JSON object
encoded as UTF-8 bytes, terminated by a single newline (NDJSON). ``send_json``
and ``recv_json_line`` are symmetric peers on either end of the TCP stream.
"""

from __future__ import annotations

import json
import socket
from typing import Any
# I use this function to send json.


def send_json(sock: socket.socket, message: dict[str, Any]) -> None:
    """Encode ``message`` as compact JSON and send with a trailing newline (one NDJSON frame)."""
    encoded = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
    sock.sendall(encoded)
# I use this function to recv json line.


def recv_json_line(sock_file: Any) -> dict[str, Any] | None:
    """
    Read one line from the stream, parse JSON, return a dict, or None if EOF/empty/closed.
    """
    raw_line = sock_file.readline()
    if not raw_line:
        return None

    line = raw_line.decode("utf-8").strip()
    if not line:
        return None
    return json.loads(line)

