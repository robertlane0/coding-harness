from __future__ import annotations

from collections import deque


class MockSocket:
    def __init__(self, data: bytes = b"") -> None:
        self._send_buffer = bytearray()
        self._recv_queue: deque[bytes] = deque()
        self._closed = False
        if data:
            self._recv_queue.append(data)

    def queue_recv(self, data: bytes) -> None:
        self._recv_queue.append(data)

    def recv(self, bufsize: int) -> bytes:
        if not self._recv_queue:
            return b""
        chunk = self._recv_queue[0]
        result = chunk[:bufsize]
        self._recv_queue[0] = chunk[bufsize:]
        if not self._recv_queue[0]:
            self._recv_queue.popleft()
        return result

    def sendall(self, data: bytes) -> None:
        self._send_buffer.extend(data)

    def close(self) -> None:
        self._closed = True

    @property
    def sent_data(self) -> bytes:
        return bytes(self._send_buffer)

    @property
    def is_closed(self) -> bool:
        return self._closed


def make_frame(
    status_line: str,
    headers: dict[str, str] | None = None,
    body: str = "",
) -> bytes:
    lines = [status_line]
    for k, v in (headers or {}).items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("")
    return "\r\n".join(lines).encode() + body.encode("utf-8")
