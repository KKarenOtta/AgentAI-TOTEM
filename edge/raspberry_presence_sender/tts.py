import os
import subprocess
import pygame
import time


def speak_welcome():
    greeting = "/home/lostgear/AgentAI-TOTEM/static/audio/greetings/greeting_pt_br.wav"
    
    if os.path.exists(greeting):
        pygame.mixer.init()
        pygame.mixer.music.load(greeting)
        pygame.mixer.music.play()
        print("Tocando greeting_pt_br.wav")
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        return
    text = "Olá, tudo bem com você? Como posso te ajudar hoje?"

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
        
if __name__ == "__main__":
    speak_welcome()
