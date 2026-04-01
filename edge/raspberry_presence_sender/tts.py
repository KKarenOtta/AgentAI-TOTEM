import os
import subprocess


def speak_welcome():
    text = "Olá, como posso te ajudar hoje?"

    print("[TTS] falando mensagem inicial")

    # tenta espeak (leve e offline)
    if os.system("which espeak > /dev/null 2>&1") == 0:
        subprocess.run(["espeak", "-v", "pt-br", text])
        return

    # fallback: festival
    if os.system("which festival > /dev/null 2>&1") == 0:
        subprocess.run(["festival", "--tts"], input=text.encode())
        return

    print("[TTS] nenhum mecanismo de voz disponível")
