from __future__ import annotations

import sys
from pathlib import Path

# === FIX DE PATH (CRÍTICO) ===
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# =============================

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

from edge.voice_agent import capture_once


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/capture":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body.decode())
            session_id = data.get("session_id")

            print("[VOICE SERVER] trigger recebido:", session_id)

            capture_once(session_id)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        except Exception as e:
            print("[VOICE SERVER] erro:", e)

            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


def run():
    print("Voice server rodando em :8001")
    server = HTTPServer(("0.0.0.0", 8001), Handler)
    server.serve_forever()


if __name__ == "__main__":
    run()
