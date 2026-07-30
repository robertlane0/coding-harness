from __future__ import annotations

from coding_harness.server import get_input


class TestServerUtils:
    def test_get_input_eof(self, monkeypatch) -> None:
        monkeypatch.setattr("sys.stdin", type("Stdin", (), {"readline": lambda self: "EOF\n"})())
        result = get_input()
        assert result == ""

    def test_get_input_multiple_lines(self, monkeypatch) -> None:
        inputs = iter(["line1\n", "line2\n", "EOF\n"])

        class FakeStdin:
            def readline(self) -> str:
                return next(inputs)

        monkeypatch.setattr("sys.stdin", FakeStdin())
        result = get_input()
        assert result == "line1\nline2"
