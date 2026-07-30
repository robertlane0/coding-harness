from __future__ import annotations

from coding_harness.client import HTPClient
from tests.conftest import MockSocket, make_frame


class TestHTPClient:
    def test_connect_and_send_request(self) -> None:
        client = HTPClient("127.0.0.1", 9999)
        mock = MockSocket()
        client.sock = mock

        client.send_request(
            "GENERATE",
            "/v1/code/completion",
            {"Client-Agent": "Test/1.0"},
            "hello",
        )
        sent = mock.sent_data
        assert b"GENERATE /v1/code/completion HTP/1.0" in sent
        assert b"content-length: 5" in sent or b"Content-Length: 5" in sent
        assert b"hello" in sent

    def test_receive_response_success(self) -> None:
        client = HTPClient("127.0.0.1", 9999)
        raw = make_frame(
            "HTP/1.0 200 OK",
            {"Content-Length": "15"},
            "def foo(): pass",
        )
        client.sock = MockSocket(raw)

        status, headers, body = client.receive_response()
        assert status == "HTP/1.0 200 OK"
        assert body == "def foo(): pass"
        assert headers["content-length"] == "15"

    def test_receive_response_empty(self) -> None:
        client = HTPClient("127.0.0.1", 9999)
        client.sock = MockSocket(b"")

        status, headers, body = client.receive_response()
        assert status is None
        assert body == ""

    def test_client_close(self) -> None:
        client = HTPClient("127.0.0.1", 9999)
        mock = MockSocket()
        client.sock = mock
        client.close()
        assert mock.is_closed
        assert client.sock is None
