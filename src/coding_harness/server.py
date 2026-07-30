from __future__ import annotations

import argparse
import logging
import os
import socket
import sys

from coding_harness.htp import build_frame, read_frame

logger = logging.getLogger("coding_harness.server")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999


def get_input(prompt: str = "") -> str:
    lines: list[str] = []
    print(prompt)
    while True:
        try:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)

    logger.info("Test server listening on %s:%s", host, port)
    print(f"\033[92m[TEST SERVER LISTENING]\033[0m http-like socket on {host}:{port}")
    print("Waiting for connection from AI Coding Harness...\n")

    conn, addr = server_sock.accept()
    logger.info("Client connected from %s:%s", addr[0], addr[1])
    print(f"\033[96m[CONNECTED]\033[0m Client connected from {addr[0]}:{addr[1]}\n")

    try:
        while True:
            frame = read_frame(conn)
            if frame is None:
                logger.info("Client closed connection")
                print("\033[91m[DISCONNECTED]\033[0m Client closed connection.")
                break

            print("\033[93m" + "=" * 60)
            print(">>> INCOMING HTP REQUEST FROM HARNESS >>>")
            print("=" * 60 + "\033[0m")
            print(f"\033[1m{frame.status_line}\033[0m")
            for k, v in frame.headers.items():
                print(f"  \033[36m{k}\033[0m: {v}")
            print("\033[90m--- Payload Body ---\033[0m")
            print(frame.body)
            print("\033[93m" + "=" * 60 + "\033[0m\n")

            print("\033[92m[SERVER INPUT]\033[0m Enter response content for harness.")
            response_body = get_input("(Type line by line. Enter 'EOF' on a new line to send):\n")

            response = build_frame(
                "HTP/1.0 200 OK",
                headers={"Content-Type": "text/plain"},
                body=response_body,
            )
            conn.sendall(response)
            logger.info("Sent response (%d bytes)", len(response))
            print("\n\033[94m[SENT]\033[0m Response frame transmitted to harness.\n")

    except Exception as e:
        logger.exception("Server error: %s", e)
        print(f"\033[91m[ERROR]\033[0m {e}")
    finally:
        conn.close()
        server_sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding Harness Test Server")
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
