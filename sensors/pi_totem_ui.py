import os, time, json, uuid, threading
import requests
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG ==================
TOTEM_API = os.getenv("TOTEM_API_URL", "http://localhost:9000/totem/interact")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")
SESSION_ID = os.getenv("SESSION_ID", f"sess-{uuid.uuid4().hex[:8]}")
PREFER_AUDIO = os.getenv("PREFER_AUDIO", "true").lower() == "true"
PIR_PIN = int(os.getenv("PIR_PIN", "17"))

# ================== GPIO Presence (PIR) ==================
PIR_AVAILABLE = True
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)
except Exception:
    PIR_AVAILABLE = False

# ================== Optional sensors (DHT/RTC) ==================
DHT_AVAILABLE = False
RTC_AVAILABLE = False
dht = None
rtc = None

try:
    import board
    import adafruit_dht
    dht = adafruit_dht.DHT22(board.D4)  # GPIO4
    DHT_AVAILABLE = True
except Exception:
    DHT_AVAILABLE = False

try:
    import busio
    import adafruit_ds3231
    import board
    i2c = busio.I2C(board.SCL, board.SDA)
    rtc = adafruit_ds3231.DS3231(i2c)
    RTC_AVAILABLE = True
except Exception:
    RTC_AVAILABLE = False

# ================== UI (Tkinter) ==================
import tkinter as tk
from tkinter import ttk

AGE_OPTIONS = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

INTENT_OPTIONS = [
    ("Promoções", "Quais promoções estão ativas para mim hoje?"),
    ("Produtos", "Me recomende produtos/ofertas ideais para mim hoje."),
    ("Suporte", "Preciso de ajuda/atendimento. Como posso resolver?"),
]

def read_env_data():
    temp = hum = None
    if DHT_AVAILABLE:
        try:
            temp = dht.temperature
            hum = dht.humidity
        except Exception:
            pass

    rtc_iso = None
    if RTC_AVAILABLE:
        try:
            rtc_iso = time.strftime("%Y-%m-%dT%H:%M:%S", rtc.datetime)
        except Exception:
            rtc_iso = None

    return temp, hum, rtc_iso

def presence_detected():
    if not PIR_AVAILABLE:
        return False
    try:
        return GPIO.input(PIR_PIN) == 1
    except Exception:
        return False

def call_backend(message: str, profile: dict):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": SESSION_ID,
        "message": message,
        "prefer_audio": PREFER_AUDIO,
        "profile": profile,
    }
    r = requests.post(TOTEM_API, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

class TotemApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Totem I.A.Gora - Raspberry Pi")
        self.attributes("-fullscreen", True)  # fullscreen kiosk
        self.configure(bg="black")

        self.state = "standby"
        self.selected_age = None
        self.selected_intent = None

        self.cooldown_s = 6
        self._last_trigger = 0

        self.container = tk.Frame(self, bg="black")
        self.container.pack(fill="both", expand=True)

        # Header
        self.header = tk.Label(
            self.container, text="Totem I.A.Gora",
            font=("Arial", 30, "bold"), fg="#00ff99", bg="black"
        )
        self.header.pack(pady=20)

        # Content frame
        self.content = tk.Frame(self.container, bg="black")
        self.content.pack(fill="both", expand=True)

        # Footer
        self.footer = tk.Label(
            self.container, text="",
            font=("Arial", 14), fg="#aaaaaa", bg="black"
        )
        self.footer.pack(pady=10)

        # Escape (dev)
        self.bind("<Escape>", lambda e: self.quit_app())

        self.render_standby()
        self.after(200, self.poll_presence)

    def quit_app(self):
        try:
            if PIR_AVAILABLE:
                GPIO.cleanup()
        except Exception:
            pass
        self.destroy()

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def render_standby(self):
        self.state = "standby"
        self.clear_content()
        msg = "Aproxime-se para iniciar"
        if not PIR_AVAILABLE:
            msg += "\n(PIR não detectado — pressione 'I' para simular)"
            self.bind("i", lambda e: self.on_presence_trigger())
            self.bind("I", lambda e: self.on_presence_trigger())

        label = tk.Label(
            self.content, text=msg,
            font=("Arial", 40, "bold"), fg="white", bg="black", justify="center"
        )
        label.pack(expand=True)

        self.footer.configure(text=f"Empresa: {COMPANY_ID} | Sessão: {SESSION_ID}")

    def render_age_question(self):
        self.state = "age"
        self.clear_content()

        label = tk.Label(
            self.content, text="Selecione sua faixa etária:",
            font=("Arial", 34, "bold"), fg="white", bg="black"
        )
        label.pack(pady=20)

        grid = tk.Frame(self.content, bg="black")
        grid.pack(pady=10)

        for idx, age in enumerate(AGE_OPTIONS):
            btn = tk.Button(
                grid, text=age,
                font=("Arial", 28, "bold"),
                width=8, height=2,
                bg="#1f1f1f", fg="white",
                activebackground="#00ff99", activeforeground="black",
                command=lambda a=age: self.on_age_selected(a)
            )
            r = idx // 4
            c = idx % 4
            btn.grid(row=r, column=c, padx=10, pady=10)

        back = tk.Button(
            self.content, text="Voltar",
            font=("Arial", 20), bg="#333", fg="white",
            command=self.render_standby
        )
        back.pack(pady=20)

    def render_intent_question(self):
        self.state = "intent"
        self.clear_content()

        label = tk.Label(
            self.content, text="O que você procura hoje?",
            font=("Arial", 34, "bold"), fg="white", bg="black"
        )
        label.pack(pady=20)

        for title, msg in INTENT_OPTIONS:
            btn = tk.Button(
                self.content, text=title,
                font=("Arial", 28, "bold"),
                width=20, height=2,
                bg="#1f1f1f", fg="white",
                activebackground="#00ff99", activeforeground="black",
                command=lambda m=msg: self.on_intent_selected(m)
            )
            btn.pack(pady=10)

        back = tk.Button(
            self.content, text="Voltar",
            font=("Arial", 20), bg="#333", fg="white",
            command=self.render_age_question
        )
        back.pack(pady=20)

    def render_processing(self):
        self.state = "processing"
        self.clear_content()
        label = tk.Label(
            self.content, text="Processando...",
            font=("Arial", 40, "bold"), fg="#ffcc00", bg="black"
        )
        label.pack(expand=True)

    def render_result(self, text: str, recs: dict):
        self.state = "result"
        self.clear_content()

        title = tk.Label(
            self.content, text="Resultado",
            font=("Arial", 34, "bold"), fg="#00ff99", bg="black"
        )
        title.pack(pady=10)

        # response text
        txt = tk.Text(self.content, wrap="word", font=("Arial", 22), height=10, bg="#111", fg="white")
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=30, pady=10)

        # recs (simplificado)
        rec_title = tk.Label(self.content, text="Sugestões:", font=("Arial", 26, "bold"), fg="white", bg="black")
        rec_title.pack(pady=5)

        actions = (recs or {}).get("top_actions", [])
        rec_box = tk.Text(self.content, wrap="word", font=("Arial", 18), height=6, bg="#111", fg="white")
        for a in actions[:5]:
            rec_box.insert("end", f"• {a.get('action')}  ({a.get('why')})\n")
        rec_box.configure(state="disabled")
        rec_box.pack(fill="x", padx=30, pady=10)

        btn_frame = tk.Frame(self.content, bg="black")
        btn_frame.pack(pady=20)

        restart = tk.Button(
            btn_frame, text="Nova interação",
            font=("Arial", 20, "bold"),
            bg="#00ff99", fg="black",
            width=16, height=2,
            command=self.render_standby
        )
        restart.grid(row=0, column=0, padx=10)

        close = tk.Button(
            btn_frame, text="Encerrar",
            font=("Arial", 20),
            bg="#333", fg="white",
            width=16, height=2,
            command=self.quit_app
        )
        close.grid(row=0, column=1, padx=10)

    def on_presence_trigger(self):
        self.render_age_question()

    def on_age_selected(self, age_range: str):
        self.selected_age = age_range
        self.render_intent_question()

    def on_intent_selected(self, message: str):
        self.selected_intent = message
        self.render_processing()

        # call backend in background thread to keep UI responsive
        t = threading.Thread(target=self._backend_flow, daemon=True)
        t.start()

    def _backend_flow(self):
        temp, hum, rtc_iso = read_env_data()

        profile = {
            "age_range": self.selected_age,
            "gender": "unknown",
            "confidence": None,
            "segment": "new_visitor",
            "device": "totem_rpi",
            "locale": "pt-BR",
            "extra": {
                "temp_c": temp,
                "humidity_pct": hum,
                "rtc_iso": rtc_iso,
                "presence_mode": "pir" if PIR_AVAILABLE else "simulated",
            }
        }

        try:
            resp = call_backend(self.selected_intent, profile)
            text = resp.get("text", "")
            recs = resp.get("recommendations", {})
            self.after(0, lambda: self.render_result(text, recs))
        except Exception as e:
            self.after(0, lambda: self.render_result(f"Erro ao conectar no servidor.\n\nDetalhes: {e}", {}))

    def poll_presence(self):
        # só detecta presença no standby
        if self.state == "standby":
            now = time.time()
            if presence_detected() and (now - self._last_trigger) > self.cooldown_s:
                self._last_trigger = now
                self.on_presence_trigger()

        self.after(200, self.poll_presence)

if __name__ == "__main__":
    app = TotemApp()
    app.mainloop()