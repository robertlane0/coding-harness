from __future__ import annotations

from coding_harness.tools import BUILTIN_TOOLS, Tool, ToolParameter, ToolRegistry


class TestTool:
    def test_format_prompt_no_context(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="You are a test assistant.",
        )
        result = tool.format_prompt(user_input="hello", context="")
        assert result == "You are a test assistant.\n\nhello"

    def test_format_prompt_with_context(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="You are a test assistant.",
        )
        result = tool.format_prompt(user_input="hello", context="file contents")
        assert result == "file contents\n\nYou are a test assistant.\n\nhello"

    def test_format_prompt_no_user_input(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="You are a test assistant.",
        )
        result = tool.format_prompt(user_input="", context="")
        assert result == "You are a test assistant."

    def test_tool_with_parameters(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="Template",
            parameters=[
                ToolParameter(name="framework", description="Test framework"),
            ],
        )
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "framework"


class TestToolRegistry:
    def test_default_tools(self) -> None:
        registry = ToolRegistry()
        assert len(registry.list_tools()) == len(BUILTIN_TOOLS)

    def test_get_tool(self) -> None:
        registry = ToolRegistry()
        tool = registry.get("explain")
        assert tool is not None
        assert tool.name == "explain"

    def test_get_unknown_tool(self) -> None:
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_register_custom_tool(self) -> None:
        registry = ToolRegistry()
        custom = Tool(name="custom", description="My tool", prompt_template="Do something")
        registry.register(custom)
        assert registry.get("custom") is custom
        assert len(registry.list_tools()) == len(BUILTIN_TOOLS) + 1

    def test_list_contains_all_builtins(self) -> None:
        registry = ToolRegistry()
        names = {t.name for t in registry.list_tools()}
        expected = {"explain", "review", "refactor", "test", "doc", "fix", "optimize"}
        assert names == expected
