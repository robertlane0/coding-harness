from __future__ import annotations

import os
import tempfile

from coding_harness.llm_tools import (
    EditFileTool,
    ReadFileTool,
    RespondTool,
    RunCommandTool,
    ToolCall,
    WriteFileTool,
    execute_tool_call,
    get_tool_specs,
)


class TestReadFileTool:
    def test_read_existing_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            path = f.name
        try:
            tool = ReadFileTool()
            result = tool.execute({"path": path})
            assert result.error is None
            assert result.output == "hello world"
        finally:
            os.unlink(path)

    def test_read_nonexistent_file(self) -> None:
        tool = ReadFileTool()
        result = tool.execute({"path": "/nonexistent/path.txt"})
        assert result.error is not None
        assert "not found" in result.error

    def test_missing_path_arg(self) -> None:
        tool = ReadFileTool()
        result = tool.execute({})
        assert result.error is not None
        assert "Missing" in result.error


class TestWriteFileTool:
    def test_write_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new_file.txt")
            tool = WriteFileTool()
            result = tool.execute({"path": path, "content": "test content"})
            assert result.error is None
            assert os.path.exists(path)
            with open(path) as f:
                assert f.read() == "test content"

    def test_missing_path(self) -> None:
        tool = WriteFileTool()
        result = tool.execute({"content": "data"})
        assert result.error is not None


class TestEditFileTool:
    def test_find_and_replace(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world world")
            path = f.name
        try:
            tool = EditFileTool()
            result = tool.execute({"path": path, "old": "world", "new": "there"})
            assert result.error is None
            assert "2 occurrence" in result.output
            with open(path) as f:
                assert f.read() == "hello there there"
        finally:
            os.unlink(path)

    def test_text_not_found(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello")
            path = f.name
        try:
            tool = EditFileTool()
            result = tool.execute({"path": path, "old": "nonexistent", "new": "x"})
            assert result.error is not None
            assert "not found" in result.error
        finally:
            os.unlink(path)


class TestRunCommandTool:
    def test_successful_command(self) -> None:
        tool = RunCommandTool()
        result = tool.execute({"command": "echo hello"})
        assert result.error is None
        assert "hello" in result.output

    def test_failing_command(self) -> None:
        tool = RunCommandTool()
        result = tool.execute({"command": "false"})
        assert result.error is None  # no exception, just non-zero exit
        assert "exit code: 1" in result.output

    def test_missing_command(self) -> None:
        tool = RunCommandTool()
        result = tool.execute({})
        assert result.error is not None


class TestRespondTool:
    def test_respond_with_message(self) -> None:
        tool = RespondTool()
        result = tool.execute({"message": "Hello user!"})
        assert result.error is None
        assert result.output == "Hello user!"

    def test_respond_empty(self) -> None:
        tool = RespondTool()
        result = tool.execute({"message": ""})
        assert result.error is None
        assert result.output == ""


class TestExecuteToolCall:
    def test_known_tool(self) -> None:
        result = execute_tool_call(ToolCall(name="respond", arguments={"message": "hi"}))
        assert result.error is None
        assert result.output == "hi"

    def test_unknown_tool(self) -> None:
        result = execute_tool_call(ToolCall(name="nonexistent"))
        assert result.error is not None
        assert "Unknown" in result.error


class TestGetToolSpecs:
    def test_contains_all_tools(self) -> None:
        specs = get_tool_specs()
        names = {s["name"] for s in specs}
        assert names == {"read_file", "write_file", "edit_file", "run_command", "respond"}

    def test_each_tool_has_description(self) -> None:
        specs = get_tool_specs()
        for s in specs:
            assert s["description"]
            assert "name" in s
            assert "parameters" in s
