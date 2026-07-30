from __future__ import annotations

from pathlib import Path

from coding_harness.tools import (
    BUILTIN_TOOLS,
    Tool,
    ToolParameter,
    ToolRegistry,
    load_tools_from_config,
)


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

    def test_format_prompt_with_param_substitution(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="Use the {framework} framework.",
        )
        result = tool.format_prompt(
            user_input="write tests",
            context="",
            params={"framework": "pytest"},
        )
        assert result == "Use the pytest framework.\n\nwrite tests"

    def test_format_prompt_unused_params_ignored(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="Hello {name}.",
        )
        result = tool.format_prompt(
            user_input="",
            context="",
            params={"name": "World", "unused": "ignored"},
        )
        assert result == "Hello World."

    def test_format_prompt_missing_param_left_as_is(self) -> None:
        tool = Tool(
            name="test",
            description="test tool",
            prompt_template="Hello {name}.",
        )
        result = tool.format_prompt(user_input="", context="")
        assert result == "Hello {name}."

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

    def test_tool_parameter_required_default(self) -> None:
        p = ToolParameter(name="x", description="X")
        assert not p.required


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
        registry = ToolRegistry(tools=[])
        custom = Tool(name="custom", description="My tool", prompt_template="Do something")
        registry.register(custom)
        assert registry.get("custom") is custom
        assert len(registry.list_tools()) == 1

    def test_register_overrides_builtin(self) -> None:
        registry = ToolRegistry()
        override = Tool(name="explain", description="Custom explain", prompt_template="Custom")
        registry.register(override)
        assert registry.get("explain").description == "Custom explain"

    def test_list_contains_all_builtins(self) -> None:
        registry = ToolRegistry()
        names = {t.name for t in registry.list_tools()}
        expected = {"explain", "review", "refactor", "test", "doc", "fix", "optimize"}
        assert names == expected


class TestLoadToolsFromConfig:
    def test_missing_file(self, tmp_path: Path) -> None:
        result = load_tools_from_config(tmp_path / "nonexistent.toml")
        assert result == []

    def test_valid_config(self, tmp_path: Path) -> None:
        config = tmp_path / "tools.toml"
        config.write_text(
            "[[tool]]\n"
            'name = "my-tool"\n'
            'description = "My custom tool"\n'
            'prompt_template = "You are a {role} expert."\n'
            "\n"
            "[[tool]]\n"
            'name = "another"\n'
            'description = "Another tool"\n'
            'prompt_template = "Just do it."\n'
        )
        tools = load_tools_from_config(config)
        assert len(tools) == 2
        assert tools[0].name == "my-tool"
        assert tools[0].prompt_template == "You are a {role} expert."
        assert tools[1].name == "another"

    def test_config_with_parameters(self, tmp_path: Path) -> None:
        config = tmp_path / "tools.toml"
        config.write_text(
            "[[tool]]\n"
            'name = "linter"\n'
            'description = "Lint check"\n'
            'prompt_template = "Use {linter} to check."\n'
            "\n"
            "[[tool.parameters]]\n"
            'name = "linter"\n'
            'description = "Linter name"\n'
            "required = true\n"
        )
        tools = load_tools_from_config(config)
        assert len(tools) == 1
        assert len(tools[0].parameters) == 1
        assert tools[0].parameters[0].name == "linter"
        assert tools[0].parameters[0].required
