from __future__ import annotations

import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edge.voice_agent import capture_audio_payload

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


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length <= 0:
        return {}

    raw_body = handler.rfile.read(content_length)
    if not raw_body:
        return {}

    return json.loads(raw_body.decode("utf-8"))


def send_json(
    handler: BaseHTTPRequestHandler,
    status_code: int,
    payload: dict[str, Any],
) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            send_json(
                self,
                200,
                {
                    "ok": True,
                    "service": "totem-voice-server",
                    "mode": "capture_audio_only",
                },
            )
            return

        send_json(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path not in {"/capture", "/capture-audio"}:
            send_json(self, 404, {"ok": False, "error": "not_found"})
            return

        try:
            payload = read_json(self)
            session_id = (payload.get("session_id") or "").strip()

            if not session_id:
                send_json(
                    self,
                    400,
                    {
                        "ok": False,
                        "error": "session_id obrigatório",
                    },
                )
                return

            print("[VOICE SERVER] capture:", session_id)
            result = capture_audio_payload(session_id)
            status_code = 200 if result.get("ok") else 422

            send_json(self, status_code, result)

        except Exception as exc:
            print("[VOICE SERVER] erro:", exc)
            send_json(
                self,
                500,
                {
                    "ok": False,
                    "error": str(exc),
                },
            )


def run() -> None:
    local_ip = get_local_ip()

    print("")
    print("=" * 60)
    print("VOICE SERVER ONLINE")
    print(f"Local : http://127.0.0.1:{PORT}")
    print(f"Rede  : http://{local_ip}:{PORT}")
    print("Modo  : captura de áudio apenas; STT/TTS ficam no backend")
    print("=" * 60)
    print("")

    server = HTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    run()
