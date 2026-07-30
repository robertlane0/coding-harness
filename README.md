# Coding Harness

A custom AI coding assistant framework featuring **HTP (Harness Text Protocol v1.0)** —
an HTTP-like, line-based, JSONless binary/text protocol — with a terminal client
using [`rich`](https://github.com/Textualize/rich) and an interactive test server.

## Protocol Specification (HTP/1.0)

HTP uses key-value headers terminated by double newlines (`\r\n\r\n`), followed by
raw UTF-8 content whose byte count is specified by a `Content-Length` header.

### Request Frame

```
GENERATE /v1/completion HTP/1.0\r\n
Client-Agent: TerminalHarness/1.0\r\n
Content-Length: 38\r\n
\r\n
Write a function to binary search an array.
```

### Response Frame

```
HTP/1.0 200 OK\r\n
Server: Python-Coding-Harness/1.0\r\n
Content-Length: 68\r\n
\r\n
def binary_search(arr, target):
    # implementation here
```

## Installation

```bash
uv sync
```

For development (linting, type-checking, tests):

```bash
uv sync --extra dev
```

## Usage

**Terminal 1** — Start the test server:

```bash
uv run python server.py          # or: uv run coding-harness-server
uv run python server.py --help   # show options
```

**Terminal 2** — Start the harness client:

```bash
uv run python client.py          # or: uv run coding-harness-client
uv run python client.py --help   # show options
```

### Workflow

1. Start the server in one terminal.
2. Start the client in another.
3. Type a prompt in the client, e.g. "Write a quicksort function in Python".
4. Switch to the server terminal to see the decoded HTP request and enter a mock
   AI response. End your response with `EOF` on a new line.
5. Switch back to the client to see the syntax-highlighted response.

## Client Commands

| Command | Description |
|---------|-------------|
| `/attach <file>` | Attach a file as context |
| `/clear-context` | Clear attached file context |
| `/history` | Show conversation history |
| `/clear-history` | Clear conversation history |
| `/tools` | List available tools |
| `/tool <name> [args]` | Activate a tool (optional `key=value` params) |
| `/tool-info <name>` | Show detailed tool info |
| `/deactivate` | Deactivate the current tool |
| `/exit` | Exit the session |

## Built-in Tools

| Tool | Description | Params |
|------|-------------|--------|
| `explain` | Explain code in detail | — |
| `review` | Review code for bugs, style, security | — |
| `refactor` | Suggest refactoring improvements | — |
| `test` | Generate unit tests | `framework` |
| `doc` | Generate documentation | — |
| `fix` | Identify and fix bugs | — |
| `optimize` | Suggest performance optimizations | — |

Activate a tool with `/tool <name>`. Subsequent prompts get the tool's prompt
template prepended. Pass parameters inline: `/tool test framework=pytest`.

## Custom Tools

Define tools in TOML config files:

- `./.coding-harness.toml`
- `~/.config/coding-harness/tools.toml`

```toml
[[tool]]
name = "summarize"
description = "Summarize the given code"
prompt_template = "Summarize the following code concisely."

[[tool]]
name = "translate"
description = "Translate code between languages"
prompt_template = "Translate this code from {source_lang} to {target_lang}."
[[tool.parameters]]
name = "source_lang"
required = true
[[tool.parameters]]
name = "target_lang"
required = true
```

## Server Options

```
uv run python server.py --help
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Listen address |
| `--port PORT` | `9999` | Listen port |
| `--no-color` | — | Disable ANSI color output |
| `-v` / `--verbose` | — | Enable debug logging |

The server handles multiple clients sequentially. Use Ctrl-C for graceful shutdown.

## Client Options

```
uv run python client.py --help
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Server address |
| `--port PORT` | `9999` | Server port |

Environment variables `HOST` and `PORT` are also respected by both server and client.

## Development

```bash
uv run ruff check          # lint
uv run ruff format --check # format check
uv run mypy src/           # type check
uv run pytest -v           # run tests
uv run pytest --cov=src    # test with coverage
```

## Project Structure

```
src/coding_harness/
  __init__.py      # Package exports
  __main__.py      # python -m coding_harness <server|client>
  htp.py           # HTP protocol frame parsing/building
  server.py        # Interactive test server
  client.py        # Rich terminal client
  tools.py         # Tool system (built-in + config-loaded)
tests/
  test_htp.py      # HTP protocol unit tests
  test_server.py   # Server utility tests
  test_client.py   # Client unit tests
  test_tools.py    # Tool system tests
```

## License

MIT
