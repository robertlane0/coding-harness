from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolParameter:
    name: str
    description: str
    required: bool = False


@dataclass
class Tool:
    name: str
    description: str
    prompt_template: str
    parameters: list[ToolParameter] = field(default_factory=list)

    def format_prompt(
        self,
        user_input: str = "",
        context: str = "",
        params: dict[str, str] | None = None,
    ) -> str:
        filled = self.prompt_template
        if params:
            for k, v in params.items():
                filled = filled.replace(f"{{{k}}}", v)
        parts: list[str] = []
        if context:
            parts.append(context)
        parts.append(filled)
        if user_input:
            parts.append(user_input)
        return "\n\n".join(parts)


BUILTIN_TOOLS: list[Tool] = [
    Tool(
        name="explain",
        description="Explain the given code in detail",
        prompt_template=(
            "You are a code explanation assistant. "
            "Explain the following code in detail, covering what it does, "
            "how it works, and any notable patterns or pitfalls."
        ),
    ),
    Tool(
        name="review",
        description="Review code for bugs, style, and improvements",
        prompt_template=(
            "You are a senior code reviewer. Review the following code for:\n"
            "- Correctness and potential bugs\n"
            "- Code style and readability\n"
            "- Performance concerns\n"
            "- Security issues\n"
            "- Suggestions for improvement"
        ),
    ),
    Tool(
        name="refactor",
        description="Suggest refactoring improvements for code",
        prompt_template=(
            "You are a code refactoring expert. Suggest specific refactoring "
            "improvements for the following code. Focus on readability, "
            "maintainability, and adherence to best practices."
        ),
    ),
    Tool(
        name="test",
        description="Generate unit tests for the given code",
        parameters=[
            ToolParameter(
                name="framework",
                description="Test framework (pytest, unittest, etc.)",
                required=False,
            ),
        ],
        prompt_template=(
            "You are a testing expert. Write comprehensive unit tests "
            "for the following code using the {framework} framework. "
            "Include edge cases and error conditions."
        ),
    ),
    Tool(
        name="doc",
        description="Generate documentation for code",
        prompt_template=(
            "You are a technical writer. Generate clear and comprehensive "
            "documentation for the following code, including description, "
            "parameters, return values, and usage examples."
        ),
    ),
    Tool(
        name="fix",
        description="Identify and fix issues in the code",
        prompt_template=(
            "You are a debugging expert. Identify bugs and issues in the "
            "following code and provide a corrected version with explanations "
            "of what was wrong and why the fix works."
        ),
    ),
    Tool(
        name="optimize",
        description="Suggest performance optimizations for code",
        prompt_template=(
            "You are a performance optimization expert. Analyze the following "
            "code for performance bottlenecks and suggest specific optimizations "
            "with benchmark considerations."
        ),
    ),
]


def _load_tool_from_dict(data: dict[str, Any]) -> Tool:
    params = [
        ToolParameter(
            name=p["name"],
            description=p.get("description", ""),
            required=p.get("required", False),
        )
        for p in data.get("parameters", [])
    ]
    return Tool(
        name=data["name"],
        description=data.get("description", ""),
        prompt_template=data["prompt_template"],
        parameters=params,
    )


def load_tools_from_config(path: str | Path) -> list[Tool]:
    config_path = Path(path).expanduser()
    if not config_path.exists():
        return []
    with config_path.open("rb") as f:
        data = tomllib.load(f)
    raw = data.get("tool", [])
    tools_data = raw if isinstance(raw, list) else [raw]
    return [
        _load_tool_from_dict(t)
        for t in tools_data
        if isinstance(t, dict) and "name" in t and "prompt_template" in t
    ]


def load_user_tools() -> list[Tool]:
    candidates = [
        Path.cwd() / ".coding-harness.toml",
        Path.home() / ".config" / "coding-harness" / "tools.toml",
    ]
    tools: list[Tool] = []
    for path in candidates:
        tools.extend(load_tools_from_config(path))
    return tools


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        builtins = tools if tools is not None else BUILTIN_TOOLS
        for tool in builtins:
            self._tools[tool.name] = tool
        for tool in load_user_tools():
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
