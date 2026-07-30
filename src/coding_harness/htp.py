from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB


@dataclass
class HTPFrame:
    status_line: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""


def read_exact(sock: socket.socket, n_bytes: int) -> bytes:
    buf = bytearray()
    while len(buf) < n_bytes:
        chunk = sock.recv(n_bytes - len(buf))
        if not chunk:
            raise ConnectionError("Socket connection closed prematurely")
        buf.extend(chunk)
    return bytes(buf)


def _read_header_bytes(sock: socket.socket) -> tuple[bytes, bytearray]:
    header_bytes = bytearray()
    while b"\r\n\r\n" not in header_bytes and b"\n\n" not in header_bytes:
        chunk = sock.recv(1)
        if not chunk:
            return b"", bytearray()
        header_bytes.extend(chunk)
    delimiter = b"\r\n\r\n" if b"\r\n\r\n" in header_bytes else b"\n\n"
    header_part, leftover = header_bytes.split(delimiter, 1)
    return bytes(header_part), leftover


def _parse_headers(header_part: bytes) -> tuple[str, dict[str, str]]:
    lines = header_part.decode("utf-8", errors="replace").splitlines()
    if not lines:
        return "", {}
    status_line = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status_line, headers


def _read_body(sock: socket.socket, headers: dict[str, str], leftover: bytearray) -> str:
    raw = headers.get("content-length", "0")
    try:
        content_len = int(raw)
    except ValueError:
        logger.warning("Invalid Content-Length: %r", raw)
        content_len = 0
    if content_len < 0 or content_len > MAX_CONTENT_LENGTH:
        logger.warning("Refusing Content-Length %d (max %d)", content_len, MAX_CONTENT_LENGTH)
        raise ValueError(f"Content-Length {content_len} out of range")
    buf = bytearray(leftover)
    while len(buf) < content_len:
        chunk = sock.recv(content_len - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return buf.decode("utf-8", errors="replace")


def read_frame(sock: socket.socket) -> HTPFrame | None:
    header_part, leftover = _read_header_bytes(sock)
    if not header_part:
        return None
    status_line, headers = _parse_headers(header_part)
    if not status_line:
        return None
    body = _read_body(sock, headers, leftover)
    return HTPFrame(status_line=status_line, headers=headers, body=body)


def build_frame(
    status_line: str,
    headers: dict[str, str] | None = None,
    body: str = "",
    *,
    server_header: str = "Python-Coding-Harness/1.0",
) -> bytes:
    body_bytes = body.encode("utf-8")
    all_headers = dict(headers or {})
    all_headers.setdefault("content-length", str(len(body_bytes)))
    all_headers.setdefault("server", server_header)

    header_lines = [status_line]
    for k, v in all_headers.items():
        header_lines.append(f"{k}: {v}")
    header_lines.append("")
    header_lines.append("")

    return "\r\n".join(header_lines).encode() + body_bytes
