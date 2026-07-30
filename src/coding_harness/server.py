from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import sys
import threading

from coding_harness.htp import build_frame, read_frame

logger = logging.getLogger("coding_harness.server")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB


def _color(code: int, text: str, use_color: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if use_color else text


def get_input(prompt: str = "") -> str:
    lines: list[str] = []
    if prompt:
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


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    color: bool = True,
) -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.settimeout(None)  # block indefinitely on accept
    server_sock.bind((host, port))
    server_sock.listen(1)

    logger.info("Test server listening on %s:%s", host, port)
    print(f"{_color(92, '[TEST SERVER LISTENING]', color)} http-like socket on {host}:{port}")
    print("Waiting for connection from AI Coding Harness...\n")

    shutdown_requested = False

    def handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown_requested
        logger.info("Received signal %d, shutting down...", signum)
        shutdown_requested = True

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not shutdown_requested:
            logger.info("Waiting for connection on %s:%s", host, port)
            conn: socket.socket
            conn, addr = server_sock.accept()
            conn.settimeout(30)
            logger.info("Client connected from %s:%s", addr[0], addr[1])
            print(f"{_color(96, '[CONNECTED]', color)} Client connected from {addr[0]}:{addr[1]}\n")

            try:
                while not shutdown_requested:
                    frame = read_frame(conn)
                    if frame is None:
                        logger.info("Client closed connection")
                        print(f"{_color(91, '[DISCONNECTED]', color)} Client closed connection.")
                        break

                    if shutdown_requested:
                        break

                    print(_color(93, "=" * 60, color))
                    print(">>> INCOMING HTP REQUEST FROM HARNESS >>>")
                    print(_color(93, "=" * 60, color))
                    print(f"{_color(1, frame.status_line, color)}")
                    for k, v in frame.headers.items():
                        print(f"  {_color(36, k, color)}: {v}")
                    print(f"{_color(90, '--- Payload Body ---', color)}")
                    print(frame.body)
                    print(f"{_color(93, '=' * 60, color)}\n")

                    if len(frame.body) > MAX_CONTENT_LENGTH:
                        logger.warning("Oversized request body (%d bytes)", len(frame.body))

                    inp = _color(92, "[SERVER INPUT]", color)
                    print(f"{inp} Enter response content for harness.")
                    response_body = get_input(
                        "(Type line by line. Enter 'EOF' on a new line to send):\n"
                    )

                    response = build_frame(
                        "HTP/1.0 200 OK",
                        headers={"Content-Type": "text/plain"},
                        body=response_body,
                    )
                    conn.sendall(response)
                    logger.info("Sent response (%d bytes)", len(response))
                    sent_label = _color(94, "[SENT]", color)
                    print(f"\n{sent_label} Response frame transmitted to harness.\n")

            except TimeoutError:
                logger.warning("Connection timed out")
                print(f"{_color(91, '[TIMEOUT]', color)} Connection timed out.")
            except OSError as e:
                if shutdown_requested:
                    logger.info("Socket closed during shutdown")
                else:
                    logger.exception("Socket error: %s", e)
                    print(f"{_color(91, '[ERROR]', color)} {e}")
            except Exception as e:
                logger.exception("Connection error: %s", e)
                print(f"{_color(91, '[ERROR]', color)} {e}")
            finally:
                conn.close()
                logger.info("Client disconnected")
                print(f"{_color(91, '[DISCONNECTED]', color)} Client disconnected.\n")

    except OSError as e:
        if shutdown_requested:
            logger.info("Server socket closed during shutdown")
        else:
            logger.exception("Server error: %s", e)
            print(f"{_color(91, '[ERROR]', color)} {e}")
    finally:
        server_sock.close()
        logger.info("Server shut down")


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding Harness Test Server")
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    run_server(host=args.host, port=args.port, color=not args.no_color)


if __name__ == "__main__":
    main()
