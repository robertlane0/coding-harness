# Production-Readiness Plan for Coding Harness

## Current State Assessment

**coding-harness** is a custom AI coding assistant framework using a bespoke text-based protocol (HTP/1.0) over TCP sockets. It has a client (`client.py`) and server (`server.py`) with no tests, no type annotations, no linter/formatter, no CI/CD, and `rich` is an undeclared runtime dependency.

---

## Milestones

### 1. Add Development Tooling & Declare Dependencies

**Files:** `pyproject.toml`, `ruff.toml`

- Add `rich` to `[project.dependencies]`
- Add dev dependencies: `ruff`, `mypy`, `pytest`
- Create `ruff.toml` with sensible defaults
- Add `[tool.mypy]` and `[tool.pytest.ini_options]` to `pyproject.toml`
- Add lint and type-check commands

### 2. Refactor Shared HTP Protocol into Installable Package

**New files:** `src/coding_harness/htp.py`, `src/coding_harness/server.py`, `src/coding_harness/client.py`, `src/coding_harness/__main__.py`

- Extract HTP frame parsing/building into `src/coding_harness/htp.py` (shared by server and client)
- Move server logic into `src/coding_harness/server.py` (as a module)
- Move client logic into `src/coding_harness/client.py` (as a module)
- Add `__main__.py` for `python -m coding_harness` entry
- Keep top-level `server.py` and `client.py` as thin CLI wrappers that import from the package
- Define a `dataclass` for HTP frames (status line, headers dict, body)

### 3. Add Type Annotations Throughout

- Add full type annotations to `htp.py`, `server.py`, `client.py`
- Enable `--strict` in mypy config (or near-strict)

### 4. Add Comprehensive Tests

**New files:** `tests/` directory with:
- `tests/test_htp.py` — Unit tests for HTP frame parsing/building
- `tests/test_server.py` — Unit tests for server logic (with mock sockets)
- `tests/test_client.py` — Unit tests for client logic (with mock sockets)
- `tests/conftest.py` — Shared fixtures (mock sockets, sample frames)

Aim for >80% coverage on the HTP protocol layer.

### 5. Replace ANSI Prints with Structured Logging

- Replace `print()` with `logging` throughout
- Use `logging.basicConfig` for server (plain text to stderr)
- Keep Rich console output for client (user-facing)
- Add `-v`/`--verbose` flag to control log level

### 6. Add Configuration (Env Vars / CLI Args)

- Support `HOST`, `PORT`, `LOG_LEVEL` environment variables
- Add `argparse` to both `server.py` and `client.py` for CLI overrides
- Keep sensible defaults (127.0.0.1:9999)

### 7. Graceful Shutdown & Improved Error Handling

- Add `signal` handlers (SIGINT, SIGTERM) for clean teardown
- Add socket timeouts to prevent hangs
- Add connection retry logic to client (with backoff)
- Validate user input on server side (sanitize/limit response length)
- Use `try`/`except` with specific exception types (not bare `Exception`)

### 8. Set Up CI/CD

**New files:** `.github/workflows/ci.yml`

- Run on push/PR to `main`
- Steps: lint (ruff), type-check (mypy), test (pytest), build

### 9. Hardening & Polish

- Add `ConnectionError` handling for broken sockets
- Add `Content-Length` validation (reject negative or absurdly large values)
- Support both `\r\n` and `\n` line endings robustly
- Consider moving from 1-byte-at-a-time reads to buffered reads for performance

---

## Prompt Strategy

Each milestone should be executed as a single commit with a descriptive message. After each commit, run the relevant verification commands (ruff, mypy, pytest) before proceeding. If any milestone introduces failures, stop and fix before continuing.
