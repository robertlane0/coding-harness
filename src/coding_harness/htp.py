from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

RESPONSE_TYPE_FINAL = "final"
RESPONSE_TYPE_TOOL_CALL = "tool_call"
RESPONSE_TYPE_TOOL_RESULT = "tool_result"


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


_HEADER_DELIMITERS = (b"\r\n\r\n", b"\n\n")
_BUFFER_SIZE = 8192


def _read_header_bytes(sock: socket.socket) -> tuple[bytes, bytearray]:
    buf = bytearray()
    while True:
        for delim in _HEADER_DELIMITERS:
            idx = buf.find(delim)
            if idx != -1:
                header_end = idx + len(delim)
                header_part = bytes(buf[:idx])
                leftover = bytearray(buf[header_end:])
                return header_part, leftover
        chunk = sock.recv(_BUFFER_SIZE)
        if not chunk:
            return b"" if buf else b"", bytearray(buf)  # return partial header if any
        buf.extend(chunk)


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


def get_response_type(headers: dict[str, str]) -> str:
    return headers.get("x-response-type", RESPONSE_TYPE_FINAL)


def is_tool_call(headers: dict[str, str]) -> bool:
    return get_response_type(headers) == RESPONSE_TYPE_TOOL_CALL


def parse_tool_call(headers: dict[str, str], body: str) -> dict[str, Any]:
    name = headers.get("x-tool-name", "")
    args: dict[str, str] = {}
    if body.strip():
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                args = {k: str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            for line in body.strip().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    args[k.strip()] = v.strip()
    return {"name": name, "arguments": args, "id": headers.get("x-tool-call-id", "")}


def build_tool_call_frame(
    tool_name: str,
    arguments: dict[str, str],
    *,
    call_id: str = "",
) -> bytes:
    body = json.dumps(arguments)
    headers = {
        "X-Response-Type": RESPONSE_TYPE_TOOL_CALL,
        "X-Tool-Name": tool_name,
        "Content-Type": "application/json",
    }
    if call_id:
        headers["X-Tool-Call-Id"] = call_id
    return build_frame("HTP/1.0 200 OK", headers=headers, body=body)


def build_tool_result_frame(
    tool_name: str,
    output: str,
    *,
    error: str | None = None,
    call_id: str = "",
) -> bytes:
    body = output
    headers: dict[str, str] = {
        "X-Response-Type": RESPONSE_TYPE_TOOL_RESULT,
        "X-Tool-Name": tool_name,
    }
    if error:
        headers["X-Tool-Error"] = error
    if call_id:
        headers["X-Tool-Call-Id"] = call_id
    return build_frame("HTP/1.0 200 OK", headers=headers, body=body)
