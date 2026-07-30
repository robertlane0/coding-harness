from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "server":
            from coding_harness.server import main as server_main

            sys.argv.pop(1)
            server_main()
            return
        elif cmd == "client":
            from coding_harness.client import main as client_main

            sys.argv.pop(1)
            client_main()
            return

    print("Usage: python -m coding_harness <server|client> [options]", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
