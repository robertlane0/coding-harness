from __future__ import annotations

from dataclasses import dataclass, field


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

    def format_prompt(self, user_input: str = "", context: str = "") -> str:
        parts: list[str] = []
        if context:
            parts.append(context)
        parts.append(self.prompt_template)
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
            "for the following code. Include edge cases and error conditions."
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


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or BUILTIN_TOOLS:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
