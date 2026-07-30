from __future__ import annotations

import argparse
import os
import socket
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax

from coding_harness.htp import (
    RESPONSE_TYPE_TOOL_RESULT,
    build_frame,
    get_response_type,
    is_tool_call,
    parse_tool_call,
    read_frame,
)
from coding_harness.llm_tools import (
    ToolCall,
    execute_tool_call,
    get_tool_specs,
)
from coding_harness.tools import ToolRegistry

console = Console()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999


class HTPClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body_str: str,
    ) -> None:
        assert self.sock is not None, "Client not connected"
        frame = build_frame(
            f"{method} {path} HTP/1.0",
            headers=headers,
            body=body_str,
            server_header="TerminalHarness/1.0",
        )
        self.sock.sendall(frame)

    def receive_response(self) -> tuple[str | None, dict[str, str], str]:
        assert self.sock is not None
        frame = read_frame(self.sock)
        if frame is None:
            return None, {}, ""
        return frame.status_line, frame.headers, frame.body

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding Harness Terminal Client")
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]\u26a1 Custom AI Terminal Coding Harness[/bold cyan]\n"
            "[dim]Protocol: HTP/1.0 (JSONless over TCP)[/dim]",
            border_style="cyan",
        )
    )

    client = HTPClient(args.host, args.port)
    try:
        with console.status("[yellow]Connecting to AI test server...[/yellow]"):
            client.connect()
        console.print(f"[bold green]\u2713 Connected to {args.host}:{args.port}[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]\u2717 Failed to connect to server:[/bold red] {e}")
        console.print("[dim]Make sure 'server.py' is running in another terminal window.[/dim]")
        sys.exit(1)

    attached_context = ""
    attached_filename: str | None = None
    active_tool_name: str | None = None
    conversation_history: list[str] = []
    registry = ToolRegistry()

    console.print(
        "[bold yellow]Commands:[/bold yellow]\n"
        "  [bold]/attach <file>[/bold]     Attach a file as context\n"
        "  [bold]/clear-context[/bold]     Clear attached file context\n"
        "  [bold]/history[/bold]           Show conversation history\n"
        "  [bold]/clear-history[/bold]     Clear conversation history\n"
        "  [bold]/tools[/bold]             List available tools\n"
        "  [bold]/tool <name> [args][/bold] Activate a tool (optionally with key=value params)\n"
        "  [bold]/tool-info <name>[/bold]  Show detailed info about a tool\n"
        "  [bold]/deactivate[/bold]        Deactivate the current tool\n"
        "  [bold]/exit[/bold]              Exit the session\n"
    )

    def send_with_tool_loop(
        payload: str,
        task_headers: dict[str, str],
        tool_name: str | None = None,
    ) -> bool:
        task_headers = dict(task_headers)
        task_headers["X-LLM-Tools"] = ",".join(t["name"] for t in get_tool_specs())
        current_payload = payload
        max_turns = 10

        for turn in range(max_turns):
            client.send_request("GENERATE", "/v1/code/completion", task_headers, current_payload)
            with console.status("[bold magenta]Awaiting server response...[/bold magenta]"):
                status_line, resp_headers, body = client.receive_response()
            if not status_line:
                console.print("[red]Server terminated connection unexpectedly.[/red]")
                return False

            conversation_history.append(f">>> {current_payload}")
            conversation_history.append(f"<<< ({get_response_type(resp_headers)}) {body[:100]}")

            if is_tool_call(resp_headers):
                call_info = parse_tool_call(resp_headers, body)
                call = ToolCall(
                    name=call_info["name"],
                    arguments=call_info["arguments"],
                    id=call_info["id"],
                )
                tag = f"[TOOL:{call.name}]"
                console.print(f"\n[bold green]{tag}[/bold green] Executing {call.name}...")
                console.print(f"  Args: {call.arguments}")
                result = execute_tool_call(call)
                if result.error:
                    console.print(f"  [red]Error: {result.error}[/red]")
                else:
                    preview = result.output[:200]
                    console.print(f"  Output: {preview}{'...' if len(result.output) > 200 else ''}")
                task_headers["X-Response-Type"] = RESPONSE_TYPE_TOOL_RESULT
                current_payload = result.output
                if result.error:
                    current_payload = f"Error: {result.error}"
                continue

            console.print(Rule(style="dim"))
            resp_len = resp_headers.get("content-length", "0")
            label = f" ({tool_name})" if tool_name else ""
            console.print(f"[dim]HTP Status: {status_line} | Length: {resp_len} bytes{label}[/dim]")
            if body.startswith("def ") or body.startswith("class ") or "import " in body:
                syntax = Syntax(body, "python", theme="monokai", line_numbers=True)
                title = f"Generated Code Output{label}"
                console.print(Panel(syntax, title=title, border_style="green"))
            else:
                title = f"AI Response{label}"
                console.print(Panel(body, title=title, border_style="blue"))
            console.print(Rule(style="dim"))
            print()
            return True

        console.print("[red]Tool call loop exceeded max iterations.[/red]")
        return False

    try:
        while True:
            context_name = attached_filename or "No Context"
            tool_tag = f"tool:{active_tool_name}" if active_tool_name else "No Tool"
            prompt_label = f"[bold cyan]AI-Harness[/bold cyan] [{context_name}] [{tool_tag}] >"
            user_input = Prompt.ask(prompt_label).strip()

            if not user_input:
                continue

            if user_input == "/exit":
                console.print("[dim]Exiting session...[/dim]")
                break

            if user_input == "/history":
                if not conversation_history:
                    console.print("[dim]No conversation history yet.[/dim]")
                else:
                    console.print(Rule(style="dim"))
                    console.print("[bold]Conversation History:[/bold]\n")
                    for i, entry in enumerate(conversation_history, 1):
                        label = "Prompt" if entry.startswith(">>>") else "Response"
                        console.print(f"  [bold]{i}. {label}:[/bold]")
                        content = entry[4:]  # strip >>> or <<< prefix
                        console.print(f"     {content[:200]}{'...' if len(content) > 200 else ''}")
                    console.print()
                continue

            if user_input == "/clear-history":
                conversation_history.clear()
                console.print("[yellow]Conversation history cleared.[/yellow]")
                continue

            if user_input == "/tools":
                console.print(Rule(style="dim"))
                console.print("[bold]Available Tools:[/bold]\n")
                for tool in registry.list_tools():
                    params = " ".join(f"[italic]{p.name}[/italic]" for p in tool.parameters)
                    param_str = f" [{params}]" if params else ""
                    console.print(f"  [bold cyan]/tool {tool.name}[/bold cyan]{param_str}")
                    console.print(f"    {tool.description}")
                console.print()
                continue

            if user_input == "/deactivate":
                if active_tool_name:
                    console.print(f"[yellow]Deactivated tool '{active_tool_name}'.[/yellow]")
                    active_tool_name = None
                else:
                    console.print("[dim]No active tool to deactivate.[/dim]")
                continue

            if user_input.startswith("/tool-info "):
                tool_name = user_input.split(maxsplit=1)[1].strip()
                found = registry.get(tool_name)
                if not found:
                    msg = f"Unknown tool '{tool_name}'."
                    console.print(f"[red]{msg}[/red]")
                else:
                    console.print(Rule(style="dim"))
                    console.print(f"[bold cyan]Tool:[/bold cyan] {found.name}")
                    console.print(f"[bold]Description:[/bold] {found.description}")
                    console.print(f"[bold]Prompt Template:[/bold]\n{found.prompt_template}\n")
                    if found.parameters:
                        console.print("[bold]Parameters:[/bold]")
                        for p in found.parameters:
                            req = " (required)" if p.required else ""
                            console.print(f"  [italic]{p.name}[/italic]{req}: {p.description}")
                    else:
                        console.print("[dim]No parameters.[/dim]")
                    console.print()
                continue

            if user_input.startswith("/tool "):
                parts = user_input.split(maxsplit=2)
                tool_name = parts[1] if len(parts) > 1 else ""
                tool_args = parts[2] if len(parts) > 2 else ""
                found = registry.get(tool_name)
                if not found:
                    msg = f"Unknown tool '{tool_name}'. Use /tools to list available tools."
                    console.print(f"[red]{msg}[/red]")
                    continue
                active_tool_name = tool_name
                msg = f"Tool '{tool_name}' activated. Type your prompt to use it."
                console.print(f"[green]{msg}[/green]")
                if tool_args:
                    user_input = tool_args
                else:
                    continue

            if user_input.startswith("/attach "):
                filepath = user_input.split(" ", 1)[1].strip()
                if os.path.exists(filepath):
                    with open(filepath, encoding="utf-8") as f:
                        attached_context = f.read()
                    attached_filename = os.path.basename(filepath)
                    ctx_len = len(attached_context)
                    console.print(f"[green]\u2713 Attached file context ({ctx_len} chars)[/green]")
                else:
                    console.print(f"[red]Error: File '{filepath}' not found.[/red]")
                continue

            if user_input == "/clear-context":
                attached_context = ""
                attached_filename = None
                console.print("[yellow]Cleared file context.[/yellow]")
                continue

            if active_tool_name and not user_input.startswith("/"):
                found = registry.get(active_tool_name)
                if found:
                    tool_params: dict[str, str] = {}
                    rest = user_input
                    words = user_input.split()
                    for w in words:
                        if "=" in w:
                            k, v = w.split("=", 1)
                            tool_params[k.strip()] = v.strip()
                    if tool_params:
                        param_keys = {p.name for p in found.parameters}
                        filtered = {k: v for k, v in tool_params.items() if k in param_keys}
                        rest = " ".join(
                            w
                            for w in words
                            if "=" not in w or w.split("=", 1)[0].strip() not in param_keys
                        )
                    else:
                        filtered = {}
                    payload = found.format_prompt(
                        user_input=rest,
                        context=attached_context,
                        params=filtered or None,
                    )
                    headers: dict[str, str] = {
                        "Client-Agent": "TerminalHarness/1.0",
                        "Task-Mode": f"Tool-{found.name}",
                        "Has-Context": "True" if attached_context else "False",
                        "Active-Tool": found.name,
                    }
                    if attached_filename:
                        headers["Context-Filename"] = attached_filename
                    if not send_with_tool_loop(payload, headers, tool_name=found.name):
                        break
                    continue

            headers = {
                "Client-Agent": "TerminalHarness/1.0",
                "Task-Mode": "Code-Completion",
                "Has-Context": "True" if attached_context else "False",
            }
            if attached_filename:
                headers["Context-Filename"] = attached_filename

            payload = user_input
            if attached_context:
                payload = (
                    f"--- CONTEXT ({attached_filename}) ---\n"
                    f"{attached_context}\n--- PROMPT ---\n{user_input}"
                )

            if not send_with_tool_loop(payload, headers):
                break

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user.[/dim]")
    finally:
        client.close()


if __name__ == "__main__":
    main()
