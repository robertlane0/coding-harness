from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, str] = field(default_factory=dict)
    id: str = ""


@dataclass
class ToolResult:
    name: str
    output: str
    error: str | None = None


class LLMTool:
    name: str = ""
    description: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)

    def execute(self, args: dict[str, str]) -> ToolResult:
        raise NotImplementedError


class ReadFileTool(LLMTool):
    name = "read_file"
    description = "Read the contents of a file from the filesystem"
    parameters = [
        {"name": "path", "type": "string", "description": "Path to the file", "required": True},
    ]

    def execute(self, args: dict[str, str]) -> ToolResult:
        path = args.get("path", "")
        if not path:
            return ToolResult(name=self.name, output="", error="Missing 'path' argument")
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as f:
                content = f.read()
            return ToolResult(name=self.name, output=content)
        except FileNotFoundError:
            return ToolResult(name=self.name, output="", error=f"File not found: {path}")
        except IsADirectoryError:
            return ToolResult(name=self.name, output="", error=f"Is a directory: {path}")
        except Exception as e:
            return ToolResult(name=self.name, output="", error=str(e))


class WriteFileTool(LLMTool):
    name = "write_file"
    description = "Write content to a file (creates or overwrites)"
    parameters = [
        {"name": "path", "type": "string", "description": "Path to the file", "required": True},
        {"name": "content", "type": "string", "description": "Content to write", "required": True},
    ]

    def execute(self, args: dict[str, str]) -> ToolResult:
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return ToolResult(name=self.name, output="", error="Missing 'path' argument")
        try:
            path = os.path.expanduser(path)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(name=self.name, output=f"Wrote {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(name=self.name, output="", error=str(e))


class EditFileTool(LLMTool):
    name = "edit_file"
    description = "Replace text in an existing file (find-and-replace)"
    parameters = [
        {"name": "path", "type": "string", "description": "Path to the file", "required": True},
        {"name": "old", "type": "string", "description": "Text to find", "required": True},
        {"name": "new", "type": "string", "description": "Replacement text", "required": True},
    ]

    def execute(self, args: dict[str, str]) -> ToolResult:
        path = args.get("path", "")
        old = args.get("old", "")
        new_text = args.get("new", "")
        if not path or not old:
            return ToolResult(
                name=self.name, output="", error="Missing required arguments (path, old)"
            )
        try:
            path = os.path.expanduser(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            if old not in content:
                return ToolResult(name=self.name, output="", error=f"Text not found in {path}")
            count = content.count(old)
            content = content.replace(old, new_text)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(name=self.name, output=f"Replaced {count} occurrence(s) in {path}")
        except FileNotFoundError:
            return ToolResult(name=self.name, output="", error=f"File not found: {path}")
        except Exception as e:
            return ToolResult(name=self.name, output="", error=str(e))


class RunCommandTool(LLMTool):
    name = "run_command"
    description = "Execute a shell command and return its output"
    parameters = [
        {
            "name": "command",
            "type": "string",
            "description": "Shell command to run",
            "required": True,
        },
    ]

    def execute(self, args: dict[str, str]) -> ToolResult:
        command = args.get("command", "")
        if not command:
            return ToolResult(name=self.name, output="", error="Missing 'command' argument")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return ToolResult(name=self.name, output=output.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(name=self.name, output="", error="Command timed out (30s)")
        except Exception as e:
            return ToolResult(name=self.name, output="", error=str(e))


class RespondTool(LLMTool):
    name = "respond"
    description = "Send a message to the user (displayed in the terminal)"
    parameters = [
        {
            "name": "message",
            "type": "string",
            "description": "Message to show the user",
            "required": True,
        },
    ]

    def execute(self, args: dict[str, str]) -> ToolResult:
        message = args.get("message", "")
        return ToolResult(name=self.name, output=message)


LLM_TOOL_REGISTRY: dict[str, LLMTool] = {
    t.name: t()
    for t in [
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        RunCommandTool,
        RespondTool,
    ]
}


def get_tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        }
        for t in LLM_TOOL_REGISTRY.values()
    ]


def execute_tool_call(call: ToolCall) -> ToolResult:
    tool = LLM_TOOL_REGISTRY.get(call.name)
    if not tool:
        return ToolResult(name=call.name, output="", error=f"Unknown tool: {call.name}")
    return tool.execute(call.arguments)
