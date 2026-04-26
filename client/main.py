"""
client/main.py

Entry point for the πthon Arena client:

* **Default:** Pygame app (`client.gui_app`) — login, lobby, match, game-over.
* ``--cli``: legacy terminal lobby + Pygame match window (unchanged behavior).

Networking uses ``client.net_client.ClientConnection`` only; protocol is unchanged.
"""

from __future__ import annotations

import argparse
import threading
from queue import Empty, Queue
from typing import Any

from client.gui_app import run_gui_app
from client.net_client import ClientConnection
from client.screens.game_screen import run_game_screen
from shared.protocol import (
    MSG_CHALLENGE_REQUEST,
    MSG_CHALLENGE_RESPONSE,
    MSG_ERROR,
    MSG_GAME_OVER,
    MSG_GAME_STATE,
    MSG_MATCH_START,
    MSG_CHAT_RECV,
    MSG_WATCH_OK,
    MSG_WATCH_ERROR,
    MSG_USER_LIST,
)
# I use this function to run cli client.


def run_cli_client(host: str, port: int, username_arg: str | None) -> None:
    """
    Connect, register, run the text lobby loop, then open the game window for play/spectate.

    A background thread receives all server messages and fills shared state; the main
    thread handles stdin commands until a match or spectate flow begins.
    """
    conn = ClientConnection.connect(host, port)
    print(f"Connected to {host}:{port}")

    try:
        username = (username_arg or input("Enter username: ")).strip()
        ok, message = conn.register_username(username)
        if not ok:
            print(f"Registration failed: {message}")
            return

        print(f"Registration successful. Welcome, {message}!")

        pending_challenges: Queue[str] = Queue()
        my_username = message
        spectator_mode = {"value": False}
        in_match_event = threading.Event()
        match_over_event = threading.Event()
        receiver_done = threading.Event()
        state_lock = threading.Lock()
        shared_state: dict[str, Any] = {
            "latest_game_state": None,
            "latest_game_over": None,
            "latest_users": [],
            "match_start_payload": None,
            "chat_messages": [],
        }
        # I use this function to on message.

        def on_message(msg: dict) -> None:
            """Dispatch one server JSON message: update shared state and print to the console."""
            msg_type = msg.get("type")
            payload = msg.get("payload", {})

            if msg_type == MSG_USER_LIST:
                users = payload.get("users", [])
                with state_lock:
                    shared_state["latest_users"] = users
                print("\n=== Online Users ===")
                for item in users:
                    print(f"- {item.get('username')} ({item.get('status')})")
                print("====================")
                return

            if msg_type == MSG_CHALLENGE_REQUEST:
                challenger = payload.get("from", "")
                if challenger:
                    pending_challenges.put(challenger)
                    print(f"\nIncoming challenge from '{challenger}'.")
                return

            if msg_type == MSG_CHALLENGE_RESPONSE and not payload.get("accepted", False):
                print(f"\nChallenge rejected by '{payload.get('from', 'unknown')}'.")
                return

            if msg_type == MSG_MATCH_START:
                opponent = payload.get("opponent", "unknown")
                with state_lock:
                    shared_state["match_start_payload"] = payload
                print(f"\nMatch starting... Opponent: {opponent} (match_id={payload.get('match_id', 'n/a')})")
                print("Press Enter in this terminal once to open the game window.")
                in_match_event.set()
                return

            if msg_type == MSG_WATCH_OK:
                players = payload.get("players", [])
                print(f"\nNow spectating match {payload.get('match_id', 'n/a')} players={players}")
                print("Press Enter in this terminal once to open the spectator window.")
                spectator_mode["value"] = True
                in_match_event.set()
                return

            if msg_type == MSG_WATCH_ERROR:
                print(f"\nWatch request denied: {payload.get('detail', 'Unknown error')}")
                return

            if msg_type == MSG_GAME_STATE:
                with state_lock:
                    shared_state["latest_game_state"] = payload
                return

            if msg_type == MSG_CHAT_RECV:
                chat_from = payload.get("from", "?")
                text = payload.get("text", "")
                with state_lock:
                    shared_state["chat_messages"].append({"from": chat_from, "text": text})
                    if len(shared_state["chat_messages"]) > 50:
                        shared_state["chat_messages"] = shared_state["chat_messages"][-50:]
                print(f"\n[CHAT] {chat_from}: {text}")
                return

            if msg_type == MSG_GAME_OVER:
                with state_lock:
                    shared_state["latest_game_over"] = payload
                match_over_event.set()
                winner = payload.get("winner_username")
                reason = payload.get("reason")
                health = payload.get("health_by_player", {})
                if winner:
                    print(f"\n[GAME OVER] winner={winner} reason={reason} health={health}")
                else:
                    print(f"\n[GAME OVER] draw reason={reason} health={health}")
                return

            if msg_type == MSG_ERROR:
                print(f"\nServer error: {payload.get('detail', 'Unknown error')}")
                return

            print(f"\n[Info] Received message: {msg}")
        # I use this function to receiver worker.

        def receiver_worker() -> None:
            """Block in ``receive_forever`` until disconnect; sets ``receiver_done`` in ``finally``."""
            try:
                conn.receive_forever(on_message)
            finally:
                receiver_done.set()

        receiver_thread = threading.Thread(target=receiver_worker, daemon=True)
        receiver_thread.start()

        conn.request_user_list()
        print("\nCommands: users | challenge <username> | watch | quit")

        while not in_match_event.is_set() and not match_over_event.is_set() and not receiver_done.is_set():
            try:
                challenger = pending_challenges.get_nowait()
                choice = input(f"Accept challenge from '{challenger}'? (y/n): ").strip().lower()
                conn.send_challenge_response(challenger, accepted=choice == "y")
            except Empty:
                pass

            command = input("> ").strip()
            if command == "quit":
                break
            if command == "users":
                conn.request_user_list()
                continue
            if command.startswith("challenge "):
                target = command[len("challenge ") :].strip()
                if target:
                    conn.send_challenge_request(target)
                else:
                    print("Usage: challenge <username>")
                continue
            if command == "watch":
                conn.send_watch_request()
                continue
            if command:
                print("Unknown command. Use: users | challenge <username> | watch | quit")

        if in_match_event.is_set():
            # I use this function to get latest state.

            def get_latest_state() -> dict[str, Any] | None:
                """Thread-safe read of the newest ``game_state`` payload for the game screen."""
                with state_lock:
                    value = shared_state["latest_game_state"]
                return value
            # I use this function to get game over.

            def get_game_over() -> dict[str, Any] | None:
                """Thread-safe read of the final ``game_over`` payload (or None if still playing)."""
                with state_lock:
                    value = shared_state["latest_game_over"]
                return value
            # I use this function to get chat messages.

            def get_chat_messages() -> list[dict[str, Any]]:
                """Return a copy of recent chat lines for the HUD (capped in ``on_message``)."""
                with state_lock:
                    return list(shared_state["chat_messages"])

            print("Opening Pygame game window...")
            run_game_screen(
                my_username=my_username,
                get_latest_state=get_latest_state,
                get_game_over=get_game_over,
                send_move=conn.send_move,
                send_chat=conn.send_chat,
                get_chat_messages=get_chat_messages,
                is_spectator=spectator_mode["value"],
            )
            print("Game window closed.")
    finally:
        conn.close()
# I use this function to main.


def main() -> None:
    """Entry point: parse args and either launch the GUI app or the legacy CLI lobby."""
    parser = argparse.ArgumentParser(description="πthon Arena client.")
    parser.add_argument("--host", default="127.0.0.1", help="Server IP/hostname")
    parser.add_argument("--port", type=int, default=5000, help="Server TCP port")
    parser.add_argument("--username", help="Username (GUI: prefills login field; CLI: skips prompt if set)")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use the legacy terminal lobby instead of the full GUI client.",
    )
    args = parser.parse_args()

    if args.cli:
        run_cli_client(args.host, args.port, args.username)
    else:
        run_gui_app(host=args.host, port=args.port, username_prefill=args.username)


if __name__ == "__main__":
    main()
