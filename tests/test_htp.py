from __future__ import annotations

import pytest

from coding_harness.htp import (
    HTPFrame,
    build_frame,
    read_exact,
    read_frame,
)
from tests.conftest import MockSocket, make_frame


class TestReadExact:
    def test_read_exact_success(self) -> None:
        sock = MockSocket(b"hello world")
        assert read_exact(sock, 5) == b"hello"

    def test_read_exact_connection_closed(self) -> None:
        sock = MockSocket(b"abc")
        with pytest.raises(ConnectionError, match="closed prematurely"):
            read_exact(sock, 10)


class TestReadFrame:
    def test_read_simple_frame(self) -> None:
        data = make_frame(
            "GENERATE /test HTP/1.0",
            {"Client-Agent": "Test/1.0", "Content-Length": "5"},
            "hello",
        )
        sock = MockSocket(data)
        frame = read_frame(sock)
        assert frame is not None
        assert frame.status_line == "GENERATE /test HTP/1.0"
        assert frame.headers["client-agent"] == "Test/1.0"
        assert frame.body == "hello"

    def test_read_frame_no_content(self) -> None:
        data = make_frame("HTP/1.0 200 OK", {"Content-Length": "0"}, "")
        sock = MockSocket(data)
        frame = read_frame(sock)
        assert frame is not None
        assert frame.status_line == "HTP/1.0 200 OK"
        assert frame.body == ""

    def test_read_frame_no_body_no_length(self) -> None:
        data = make_frame("PING HTP/1.0", {})
        sock = MockSocket(data)
        frame = read_frame(sock)
        assert frame is not None
        assert frame.body == ""

    def test_read_frame_empty_connection(self) -> None:
        sock = MockSocket(b"")
        frame = read_frame(sock)
        assert frame is None

    def test_read_frame_only_newlines(self) -> None:
        sock = MockSocket(b"\r\n\r\n")
        frame = read_frame(sock)
        assert frame is None

    def test_read_frame_newline_variants(self) -> None:
        data = make_frame(
            "GET /ping HTP/1.0",
            {"Content-Length": "4"},
            "pong",
        ).replace(b"\r\n", b"\n")
        sock = MockSocket(data)
        frame = read_frame(sock)
        assert frame is not None
        assert "content-length" in frame.headers
        assert frame.body == "pong"


class TestBuildFrame:
    def test_build_basic_frame(self) -> None:
        result = build_frame(
            "GENERATE /test HTP/1.0",
            headers={"X-Custom": "value"},
            body="test body",
        )
        assert b"GENERATE /test HTP/1.0" in result
        assert b"content-length: 9" in result or b"Content-Length: 9" in result
        assert b"test body" in result

    def test_build_frame_content_length_matches(self) -> None:
        result = build_frame("HTP/1.0 200 OK", body="hello")
        assert b"content-length: 5" in result

    def test_build_frame_auto_sets_content_length(self) -> None:
        result = build_frame("HTP/1.0 200 OK", body="hello")
        header_section = result.split(b"\r\n\r\n")[0].decode()
        assert "content-length: 5" in header_section

    def test_build_frame_empty_body(self) -> None:
        result = build_frame("HTP/1.0 200 OK")
        assert b"content-length: 0" in result

    def test_build_frame_roundtrip(self) -> None:
        raw = build_frame(
            "GENERATE /v1/completion HTP/1.0",
            headers={"Client-Agent": "Test/1.0"},
            body="def foo(): pass",
        )
        sock = MockSocket(raw)
        frame = read_frame(sock)
        assert frame is not None
        assert frame.status_line == "GENERATE /v1/completion HTP/1.0"
        assert frame.body == "def foo(): pass"
        assert frame.headers["client-agent"] == "Test/1.0"


class TestHTPFrame:
    def test_frame_defaults(self) -> None:
        frame = HTPFrame(status_line="HTP/1.0 200 OK")
        assert frame.headers == {}
        assert frame.body == ""

    def test_frame_with_data(self) -> None:
        frame = HTPFrame(
            status_line="GENERATE /test HTP/1.0",
            headers={"content-type": "text/plain"},
            body="data",
        )
        assert frame.headers["content-type"] == "text/plain"
        assert frame.body == "data"
