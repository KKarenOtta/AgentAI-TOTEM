from __future__ import annotations

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket

# =========================
# FIX ROOT PATH
# =========================

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# =========================

from edge.voice_agent import capture_once

HOST = "0.0.0.0"
PORT = 5000


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/capture":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            payload = json.loads(body.decode("utf-8"))

            session_id = payload.get("session_id")

            print(f"[VOICE SERVER] trigger recebido: {session_id}")

            capture_once(session_id)

            response = {
                "ok": True
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps(response).encode("utf-8")
            )

        except Exception as exc:
            print("[VOICE SERVER] erro:", exc)

            response = {
                "ok": False,
                "error": str(exc)
            }

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps(response).encode("utf-8")
            )


def run():
    local_ip = get_local_ip()

    print("")
    print("=" * 60)
    print("VOICE SERVER ONLINE")
    print(f"Local : http://127.0.0.1:{PORT}")
    print(f"Rede  : http://{local_ip}:{PORT}")
    print("=" * 60)
    print("")

    server = HTTPServer((HOST, PORT), Handler)

    server.serve_forever()


if __name__ == "__main__":
    run()
