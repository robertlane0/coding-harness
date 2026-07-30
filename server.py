import socket

HOST = "127.0.0.1"
PORT = 9999


def read_exact(sock, n_bytes):
    """Read exactly n bytes from socket."""
    buf = bytearray()
    while len(buf) < n_bytes:
        chunk = sock.recv(n_bytes - len(buf))
        if not chunk:
            raise ConnectionError("Socket connection closed prematurely")
        buf.extend(chunk)
    return bytes(buf)


def parse_htp_request(sock):
    """Parse HTP/1.0 frame: line-based headers + raw body based on Content-Length."""
    header_bytes = bytearray()
    while b"\r\n\r\n" not in header_bytes and b"\n\n" not in header_bytes:
        chunk = sock.recv(1)
        if not chunk:
            return None, None, None
        header_bytes.extend(chunk)

    delimiter = b"\r\n\r\n" if b"\r\n\r\n" in header_bytes else b"\n\n"
    header_part, leftover = header_bytes.split(delimiter, 1)

    header_lines = header_part.decode("utf-8", errors="replace").splitlines()
    if not header_lines:
        return None, None, None

    request_line = header_lines[0]
    headers = {}
    for line in header_lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    content_length = int(headers.get("content-length", 0))
    needed_body_bytes = content_length - len(leftover)

    body_bytes = leftover
    if needed_body_bytes > 0:
        body_bytes += read_exact(sock, needed_body_bytes)

    body = body_bytes.decode("utf-8", errors="replace")
    return request_line, headers, body


def run_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(1)

    print(f"\033[92m[TEST SERVER LISTENING]\033[0m http-like socket on {HOST}:{PORT}")
    print("Waiting for connection from AI Coding Harness...\n")

    conn, addr = server_sock.accept()
    print(f"\033[96m[CONNECTED]\033[0m Client connected from {addr[0]}:{addr[1]}\n")

    try:
        while True:
            req_line, headers, body = parse_htp_request(conn)
            if not req_line:
                print("\033[91m[DISCONNECTED]\033[0m Client closed connection.")
                break

            # 1. Output received request to stdout
            print("\033[93m" + "=" * 60)
            print(">>> INCOMING HTP REQUEST FROM HARNESS >>>")
            print("=" * 60 + "\033[0m")
            print(f"\033[1m{req_line}\033[0m")
            for k, v in headers.items():
                print(f"  \033[36m{k}\033[0m: {v}")
            print("\033[90m--- Payload Body ---\033[0m")
            print(body)
            print("\033[93m" + "=" * 60 + "\033[0m\n")

            # 2. Get AI response from stdin
            print("\033[92m[SERVER INPUT]\033[0m Enter response content for harness.")
            print("(Type line by line. Enter 'EOF' on a new line to send):\n")

            response_lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "EOF":
                        break
                    response_lines.append(line)
                except EOFError:
                    break

            response_body = "\n".join(response_lines)
            body_bytes = response_body.encode("utf-8")

            # 3. Build HTP response
            htp_response = (
                f"HTP/1.0 200 OK\r\n"
                f"Server: Python-Test-Server/1.0\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {len(body_bytes)}\r\n"
                f"\r\n"
            ).encode() + body_bytes

            conn.sendall(htp_response)
            print("\n\033[94m[SENT]\033[0m Response frame transmitted to harness.\n")

    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m {e}")
    finally:
        conn.close()
        server_sock.close()


if __name__ == "__main__":
    run_server()
