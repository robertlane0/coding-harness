import os
import socket
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax

console = Console()

HOST = "127.0.0.1"
PORT = 9999


class HTPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send_request(self, method, path, headers, body_str):
        body_bytes = body_str.encode("utf-8")
        headers["content-length"] = str(len(body_bytes))

        # Build raw HTTP-like request frame
        header_lines = [f"{method} {path} HTP/1.0"]
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
        header_lines.append("")
        header_lines.append("")

        frame = "\r\n".join(header_lines).encode("utf-8") + body_bytes
        self.sock.sendall(frame)

    def receive_response(self):
        header_bytes = bytearray()
        while b"\r\n\r\n" not in header_bytes and b"\n\n" not in header_bytes:
            chunk = self.sock.recv(1)
            if not chunk:
                return None, {}, ""
            header_bytes.extend(chunk)

        delimiter = b"\r\n\r\n" if b"\r\n\r\n" in header_bytes else b"\n\n"
        header_part, leftover = header_bytes.split(delimiter, 1)

        lines = header_part.decode("utf-8", errors="replace").splitlines()
        status_line = lines[0] if lines else ""

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_len = int(headers.get("content-length", 0))
        body_bytes = leftover
        while len(body_bytes) < content_len:
            chunk = self.sock.recv(content_len - len(body_bytes))
            if not chunk:
                break
            body_bytes.extend(chunk)

        return status_line, headers, body_bytes.decode("utf-8", errors="replace")

    def close(self):
        if self.sock:
            self.sock.close()


def main():
    console.print(
        Panel.fit(
            "[bold cyan]⚡ Custom AI Terminal Coding Harness[/bold cyan]\n"
            "[dim]Protocol: HTP/1.0 (JSONless over TCP)[/dim]",
            border_style="cyan",
        )
    )

    client = HTPClient(HOST, PORT)
    try:
        with console.status("[yellow]Connecting to AI test server...[/yellow]"):
            client.connect()
        console.print(f"[bold green]✓ Connected to {HOST}:{PORT}[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to connect to server:[/bold red] {e}")
        console.print("[dim]Make sure 'server.py' is running in another terminal window.[/dim]")
        sys.exit(1)

    attached_context = ""
    attached_filename = None

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
                    console.print(f"[green]✓ Attached file context ({ctx_len} chars)[/green]")
                else:
                    console.print(f"[red]Error: File '{filepath}' not found.[/red]")
                continue

            if user_input == "/clear-context":
                attached_context = ""
                attached_filename = None
                console.print("[yellow]Cleared file context.[/yellow]")
                continue

            # Build HTP Request Frame
            headers = {
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

            # Render response content
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
