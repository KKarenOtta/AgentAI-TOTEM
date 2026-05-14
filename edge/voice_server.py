from __future__ import annotations

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edge.voice_agent import capture_once

HOST = "0.0.0.0"
PORT = 5000


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        sock.close()

    return ip


def run_capture_async(session_id: str) -> None:
    try:
        capture_once(session_id)
    except Exception as exc:
        print("[VOICE SERVER] capture error:", exc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        if self.path != "/capture":
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            payload = json.loads(raw_body.decode("utf-8"))

            session_id = (payload.get("session_id") or "").strip()

            if not session_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "session_id obrigatório",
                        }
                    ).encode("utf-8")
                )
                return

            print("[VOICE SERVER] trigger:", session_id)

            thread = threading.Thread(
                target=run_capture_async,
                args=(session_id,),
                daemon=True,
            )

            thread.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    {
                        "ok": True,
                        "session_id": session_id,
                        "mode": "async",
                    }
                ).encode("utf-8")
            )

        except Exception as exc:
            print("[VOICE SERVER] erro:", exc)

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                    }
                ).encode("utf-8")
            )


def run() -> None:
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
