from __future__ import annotations

import base64
import os
import shlex
import subprocess
import time
import uuid

import requests

from config import COOLDOWN_SECONDS, COMPANY_ID, PIR_PIN, PRESENCE_HOLD_SECONDS
from pir_sensor import read_motion
from sender import send_trigger
from tts import speak_welcome
from audio import record_audio
from sender_audio import send_audio

SAMPLE_INTERVAL_SECONDS = 0.1
MIN_ACTIVE_RATIO = 0.35
WARMUP_SECONDS = 30
SESSION_TIMEOUT = 20
VOICE_RECORD_SECONDS = 4
PRE_CAPTURE_DELAY_SECONDS = 1.5

# Loop de reabordagem
NO_INPUT_RETRY_LIMIT = 3
NO_INPUT_PAUSE_SECONDS = 1.0

ACTIVATE_URL = os.getenv("TOTEM_ACTIVATE_URL", "http://127.0.0.1:8000/totem/activate")
INTERACT_URL = os.getenv("TOTEM_INTERACT_URL", "http://127.0.0.1:8000/totem/interact")
REQUEST_TIMEOUT = float(os.getenv("TOTEM_REQUEST_TIMEOUT", "30"))


def confirm_presence_window() -> bool:
    total_samples = max(1, int(PRESENCE_HOLD_SECONDS / SAMPLE_INTERVAL_SECONDS))
    active_samples = 0

    start = time.time()
    while time.time() - start < PRESENCE_HOLD_SECONDS:
        if read_motion():
            active_samples += 1
        time.sleep(SAMPLE_INTERVAL_SECONDS)

    ratio = active_samples / total_samples
    print(
        f"Janela presença | ativos={active_samples} "
        f"total={total_samples} ratio={ratio:.2f}"
    )
    return ratio >= MIN_ACTIVE_RATIO


def speak_text(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return

    safe_text = shlex.quote(text)

    try:
        subprocess.run(
            f'espeak -v pt-br {safe_text}',
            shell=True,
            check=False,
        )
    except Exception as exc:
        print(f"[VOICE] falha ao reproduzir resposta: {exc}")


def play_audio_file(audio_path: str | None) -> bool:
    audio_path = (audio_path or "").strip()
    if not audio_path:
        return False

    if not os.path.exists(audio_path):
        print(f"[VOICE] arquivo de áudio não encontrado: {audio_path}")
        return False

    player_cmds = [
        ["mpg123", audio_path],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
        ["aplay", audio_path],
    ]

    for cmd in player_cmds:
        try:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                print(f"[VOICE] tocando áudio com {cmd[0]}: {audio_path}")
                subprocess.run(cmd, check=False)
                return True
        except Exception as exc:
            print(f"[VOICE] falha ao tocar com {cmd[0]}: {exc}")

    print("[VOICE] nenhum player disponível para reproduzir áudio")
    return False


def play_audio_base64(audio_base64: str | None) -> bool:
    if not audio_base64:
        print("[VOICE] audio_base64 vazio ou ausente")
        return False

    try:
        tmp_path = "/tmp/tts_response.mp3"

        with open(tmp_path, "wb") as f:
            f.write(base64.b64decode(audio_base64))

        return play_audio_file(tmp_path)
    except Exception as exc:
        print(f"[VOICE] erro base64: {exc}")
        return False


def activate_session(session_id: str) -> str:
    try:
        response = requests.post(
            ACTIVATE_URL,
            json={
                "company_id": COMPANY_ID,
                "session_id": session_id,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            print(f"[ACTIVATE] falha: status={response.status_code}")
            print(response.text)
            return ""

        data = response.json()
        greeting = (data.get("greeting") or "").strip()
        print(f"[ACTIVATE] greeting={greeting}")
        return greeting

    except Exception as exc:
        print(f"[ACTIVATE] erro: {exc}")
        return ""


def interact_with_backend(session_id: str, user_text: str, input_mode: str) -> bool:
    user_text = (user_text or "").strip()
    if not user_text:
        print("[INTERACT] texto vazio; interação ignorada")
        return False

    try:
        response = requests.post(
            INTERACT_URL,
            json={
                "company_id": COMPANY_ID,
                "session_id": session_id,
                "message": user_text,
                "prefer_audio": True,
                "input_mode": input_mode,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            print(f"[INTERACT] falha: status={response.status_code}")
            print(response.text)
            return False

        data = response.json()

        text = (data.get("text") or "").strip()
        audio_base64 = data.get("audio_base64")

        print(f"[IA] {text}")

        if not play_audio_base64(audio_base64):
            speak_text(text)

        return True

    except Exception as exc:
        print(f"[INTERACT] erro: {exc}")
        return False


def capture_user_text() -> str:
    print("[VOICE] iniciando captura de áudio do usuário...")

    audio_path = record_audio(VOICE_RECORD_SECONDS)
    if not audio_path:
        print("[VOICE] falha ao gravar áudio")
        return ""

    user_text = send_audio(audio_path)
    if not user_text:
        print("[VOICE] falha ao transcrever áudio")
        return ""

    user_text = user_text.strip()
    print(f"[USUÁRIO] {user_text}")
    return user_text


def run_session(session_id: str) -> None:
    no_input_count = 0

    while no_input_count < NO_INPUT_RETRY_LIMIT:
        greeting = activate_session(session_id)
        if greeting:
            speak_text(greeting)
        else:
            speak_welcome()

        user_text = capture_user_text()

        if user_text:
            no_input_count = 0
            ok = interact_with_backend(
                session_id=session_id,
                user_text=user_text,
                input_mode="audio",
            )
            if ok:
                return

            print("[SESSION] resposta da IA falhou; encerrando sessão")
            return

        no_input_count += 1
        print(
            f"[SESSION] sem entrada do usuário "
            f"({no_input_count}/{NO_INPUT_RETRY_LIMIT})"
        )

        if not read_motion():
            print("[SESSION] sem presença detectada; encerrando sessão")
            return

        print("[SESSION] presença ainda detectada; repetindo abordagem")
        time.sleep(NO_INPUT_PAUSE_SECONDS)

    print("[SESSION] limite de reabordagens atingido; encerrando sessão")


def main() -> None:
    print("Presence sender iniciado")
    print(f"PIR_PIN={PIR_PIN}")
    print(f"HOLD={PRESENCE_HOLD_SECONDS}s")
    print(f"COOLDOWN={COOLDOWN_SECONDS}s")
    print(f"Aguardando estabilização do PIR por {WARMUP_SECONDS}s...")

    time.sleep(WARMUP_SECONDS)
    print("Sensor estabilizado. Monitorando presença...")

    last_trigger_time = 0.0
    last_motion_time = 0.0
    in_session = False
    session_id = ""

    while True:
        try:
            now = time.time()
            motion = read_motion()

            if motion:
                last_motion_time = now

            if in_session and (now - last_motion_time > SESSION_TIMEOUT):
                print("Sessão encerrada por inatividade")
                in_session = False
                session_id = ""

            if now - last_trigger_time < COOLDOWN_SECONDS:
                time.sleep(0.2)
                continue

            if in_session:
                time.sleep(0.2)
                continue

            if motion:
                print("Movimento detectado - validando janela do PIR...")

                if confirm_presence_window():
                    print("Janela válida - preparando captura...")
                    print(
                        f"Aguardando {PRE_CAPTURE_DELAY_SECONDS}s "
                        "para melhor enquadramento..."
                    )
                    time.sleep(PRE_CAPTURE_DELAY_SECONDS)

                    print("Capturando e enviando para AWS...")
                    accepted = send_trigger()

                    if accepted:
                        session_id = f"rpi-{uuid.uuid4().hex[:8]}"
                        print(f"Sessão iniciada: {session_id}")

                        in_session = True
                        last_trigger_time = time.time()
                        last_motion_time = time.time()

                        run_session(session_id)

                        print("[SESSION] fluxo concluído")
                        in_session = False
                        session_id = ""
                    else:
                        print("Presença rejeitada pela AWS")
                else:
                    print("Falso positivo descartado")

                time.sleep(1.0)
                continue

            time.sleep(0.2)

        except KeyboardInterrupt:
            print("\nEncerrado pelo usuário")
            break
        except Exception as exc:
            print(f"Erro no loop principal: {exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
