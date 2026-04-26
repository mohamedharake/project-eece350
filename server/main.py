"""
server/main.py

Process entry: binds a TCP listening socket and spawns ``handle_client`` per
connection (see ``server.net_server``).
"""

from __future__ import annotations

import argparse
import socket
import threading

from server.net_server import ServerState, handle_client
# I use this function to main.

def main() -> None:
    """Parse CLI args, bind TCP, and spawn one thread per accepted client connection."""
    parser = argparse.ArgumentParser(description="Python Arena server (Phase B).")
    parser.add_argument("--port", type=int, required=True, help="TCP port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host/IP to bind (default: 0.0.0.0)")
    args = parser.parse_args()

    state = ServerState()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((args.host, args.port))
        server_sock.listen()
        print(f"[*] Server listening on {args.host}:{args.port}")

        while True:
            client_sock, client_addr = server_sock.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(client_sock, client_addr, state),
                daemon=True,
            )
            thread.start()


if __name__ == "__main__":
    main()

