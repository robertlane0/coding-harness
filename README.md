# Coding Harness

A complete custom coding harness featuring **HTP (Harness Text Protocol v1.0)** — an HTTP-like, line-based, JSONless binary/text protocol — alongside a terminal client harness using [`rich`](https://github.com/Textualize/rich) and an interactive test server.

## Protocol Specification (HTP/1.0)

Instead of JSON payload bodies, HTP uses standard key-value headers terminated by double newlines (`\r\n\r\n`), followed by raw UTF-8 string content whose exact byte count is governed by a `Content-Length` header.

### Request Frame

```
GENERATE /v1/completion HTP/1.0\r\n
Task-Context: file.py\r\n
Language: python\r\n
Content-Length: 38\r\n
\r\n
Write a function to binary search an array.
```

### Response Frame

```
HTP/1.0 200 OK\r\n
Server: Custom-AI-Server/1.0\r\n
Content-Length: 68\r\n
\r\n
def binary_search(arr, target):
    # implementation here
```

## Components

### 1. Test Server (`server.py`)

Listens on a local TCP socket, parses incoming HTP frames without using any JSON libraries, displays the raw request on stdout, and waits for interactive manual input on stdin to send back to the harness.

### 2. AI Terminal Coding Harness (`client.py`)

A rich terminal client that connects to the test server, sends prompts as HTP frames, and renders responses with syntax highlighting.

## Requirements

- Python >= 3.14
- [`rich`](https://pypi.org/project/rich/) (for the client)

## Installation

```bash
pip install rich
```

## Usage

**Terminal 1** — Start the test server:

```bash
uv run python server.py
```

**Terminal 2** — Start the harness client:

```bash
uv run python client.py
```

### Testing Workflow

1. Type a prompt in the harness client (e.g., `Write a quicksort function in Python`).
2. Switch to **Terminal 1 (Server)**: Observe the decoded raw HTP request line, key-value headers, and body logged directly to stdout.
3. Enter your mock code response into Terminal 1, type `EOF` on a new line, and hit Enter.
4. Switch back to **Terminal 2 (Harness)**: Observe the rendered, syntax-highlighted code output received back over the socket.

### Client Commands

| Command | Description |
|---|---|
| `/attach <file>` | Attach a file as context for the next prompt |
| `/clear-context` | Clear the attached file context |
| `/exit` | Exit the session |
