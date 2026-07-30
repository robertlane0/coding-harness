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

from coding_harness.htp import build_frame, read_frame

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

    console.print(
        "[bold yellow]Commands:[/bold yellow] "
        "[bold]/attach <file>[/bold] | "
        "[bold]/clear-context[/bold] | "
        "[bold]/exit[/bold]\n"
    )

    try:
        while True:
            context_name = attached_filename or "No Context"
            prompt_label = f"[bold cyan]AI-Harness[/bold cyan] [{context_name}] >"
            user_input = Prompt.ask(prompt_label).strip()

            if not user_input:
                continue

            if user_input == "/exit":
                console.print("[dim]Exiting session...[/dim]")
                break

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

            headers: dict[str, str] = {
                "Client-Agent": "TerminalHarness/1.0",
                "Task-Mode": "Code-Completion",
                "Has-Context": "True" if attached_context else "False",
            }
            if attached_filename:
                headers["Context-Filename"] = attached_filename

            full_payload = user_input
            if attached_context:
                full_payload = (
                    f"--- CONTEXT ({attached_filename}) ---\n"
                    f"{attached_context}\n--- PROMPT ---\n{user_input}"
                )

            client.send_request("GENERATE", "/v1/code/completion", headers, full_payload)

            with console.status("[bold magenta]Awaiting server response...[/bold magenta]"):
                status_line, resp_headers, body = client.receive_response()

            if not status_line:
                console.print("[red]Server terminated connection unexpectedly.[/red]")
                break

            console.print(Rule(style="dim"))
            resp_len = resp_headers.get("content-length", "0")
            console.print(f"[dim]HTP Status: {status_line} | Length: {resp_len} bytes[/dim]")

            if body.startswith("def ") or body.startswith("class ") or "import " in body:
                syntax = Syntax(body, "python", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Generated Code Output", border_style="green"))
            else:
                console.print(Panel(body, title="AI Response", border_style="blue"))
            console.print(Rule(style="dim"))
            print()

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user.[/dim]")
    finally:
        client.close()


if __name__ == "__main__":
    main()
