import os
import sys
import traceback
from dotenv import load_dotenv

load_dotenv()

from sensors.pi_totem_ui import TotemApp


def print_boot_info():
    print("========================================")
    print(" Totem I.A.Gora | Raspberry Pi Launcher ")
    print("========================================")
    print(f"TOTEM_API_URL: {os.getenv('TOTEM_API_URL', 'http://localhost:9000/totem/interact')}")
    print(f"TRACK_API_URL: {os.getenv('TRACK_API_URL', 'http://localhost:9000/api/track')}")
    print(f"COMPANY_ID: {os.getenv('COMPANY_ID', 'FLX-001')}")
    print(f"PREFER_AUDIO: {os.getenv('PREFER_AUDIO', 'true')}")
    print(f"PIR_PIN: {os.getenv('PIR_PIN', '17')}")
    print(f"PRESENCE_HOLD_SECONDS: {os.getenv('PRESENCE_HOLD_SECONDS', '3')}")
    print(f"COOLDOWN_SECONDS: {os.getenv('COOLDOWN_SECONDS', '8')}")
    print("Modo: UI touchscreen + PIR HC-SR501")
    print("========================================")


def validate_environment():
    required_vars = {
        "TOTEM_API_URL": os.getenv("TOTEM_API_URL", "http://localhost:9000/totem/interact"),
        "TRACK_API_URL": os.getenv("TRACK_API_URL", "http://localhost:9000/api/track"),
        "COMPANY_ID": os.getenv("COMPANY_ID", "FLX-001"),
    }

    for key, value in required_vars.items():
        if not value:
            raise RuntimeError(f"Variável de ambiente obrigatória ausente: {key}")


def main():
    try:
        validate_environment()
        print_boot_info()

        app = TotemApp()
        app.mainloop()

    except KeyboardInterrupt:
        print("\n[PI_AGENT] Encerrado pelo usuário.")
        sys.exit(0)

    except Exception as e:
        print(f"\n[PI_AGENT] Erro fatal: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()