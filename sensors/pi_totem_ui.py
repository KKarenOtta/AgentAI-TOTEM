import tkinter as tk
import threading
import time
import uuid
import requests
import json
import qrcode
from PIL import Image, ImageTk

from sensors.pi_totem_sensor import SensorHub, Event


API_URL = "http://localhost:9000/totem/interact"
COMPANY_ID = "FLX-001"


class TotemUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Totem IA")
        self.attributes("-fullscreen", True)
        self.configure(bg="black")

        self.sensor = SensorHub()

        self.state = "standby"
        self.session_id = None
        self.selected_age = None
        self.selected_intent = None

        self.container = tk.Frame(self, bg="black")
        self.container.pack(fill="both", expand=True)

        self.content = tk.Frame(self.container, bg="black")
        self.content.pack(fill="both", expand=True)

        self.footer = tk.Label(
            self.container,
            text="",
            font=("Arial", 14),
            fg="#888",
            bg="black"
        )
        self.footer.pack(side="bottom", pady=10)

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("w", lambda e: self.on_wakeword())

        self.render_standby()
        self.after(100, self.poll_presence)

    # CORE UI
    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def update_footer(self, text):
        self.footer.config(text=text)

    # STATES
    def render_standby(self):
        self.state = "standby"
        self.session_id = None
        self.selected_age = None
        self.selected_intent = None

        self.clear_content()

        tk.Label(
            self.content,
            text="Aproxime-se para iniciar\n(presença por 3s)",
            font=("Arial", 40, "bold"),
            fg="white",
            bg="black",
            justify="center"
        ).pack(expand=True)

        self.update_footer("modo: standby")

    def render_age_selection(self):
        self.state = "age"

        self.clear_content()

        tk.Label(
            self.content,
            text="Qual sua faixa etária?",
            font=("Arial", 36, "bold"),
            fg="white",
            bg="black"
        ).pack(pady=40)

        options = ["18-24", "25-34", "35-44", "45+"]

        for opt in options:
            tk.Button(
                self.content,
                text=opt,
                font=("Arial", 28),
                width=15,
                command=lambda o=opt: self.on_age_selected(o)
            ).pack(pady=10)

        self.update_footer("selecione idade")

    def render_intents(self):
        self.state = "intent"

        self.clear_content()

        tk.Label(
            self.content,
            text="O que você procura?",
            font=("Arial", 36, "bold"),
            fg="white",
            bg="black"
        ).pack(pady=40)

        intents = [
            "Promoções",
            "Recomendações",
            "Novidades"
        ]

        for intent in intents:
            tk.Button(
                self.content,
                text=intent,
                font=("Arial", 28),
                width=20,
                command=lambda i=intent: self.on_intent_selected(i)
            ).pack(pady=10)

        self.update_footer("selecione interesse")

    def render_processing(self):
        self.state = "processing"
        self.clear_content()

        tk.Label(
            self.content,
            text="Processando...",
            font=("Arial", 36, "bold"),
            fg="white",
            bg="black"
        ).pack(expand=True)

        self.update_footer("aguarde")

    def render_result(self, text, recs):
        self.state = "result"
        self.clear_content()

        box = tk.Text(
            self.content,
            wrap="word",
            font=("Arial", 22),
            bg="black",
            fg="white"
        )
        box.insert("1.0", text)
        box.config(state="disabled")
        box.pack(fill="both", expand=True, padx=40, pady=20)

        tk.Button(
            self.content,
            text="Nova interação",
            font=("Arial", 20),
            command=self.render_standby
        ).pack(pady=20)

        self.update_footer("resultado")

        if recs:
            self.after(1000, lambda: self.show_qr(recs))

    # EVENTS
    def on_presence_trigger(self):
        if self.state != "standby":
            return

        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.sensor.log_event(Event.AWARE, session_id=self.session_id)

        self.render_age_selection()

    def on_wakeword(self):
        if self.state != "standby":
            return

        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"
        self.sensor.log_event(Event.WAKEWORD, session_id=self.session_id)

        self.render_age_selection()

    def on_age_selected(self, age):
        self.selected_age = age
        self.sensor.log_event(Event.SESSION_START, session_id=self.session_id)

        self.render_intents()

    def on_intent_selected(self, message):
        if self.state == "processing":
            return

        self.selected_intent = message
        self.render_processing()

        threading.Thread(
            target=self._backend_flow,
            daemon=True
        ).start()

    # BACKEND
    def _backend_flow(self):
        try:
            temp, hum = self.sensor.read_env()
            ts = self.sensor.read_timestamp()

            profile = {
                "age_range": self.selected_age,
                "extra": {
                    "temp_c": temp,
                    "humidity_pct": hum,
                    "ts": ts
                }
            }

            payload = {
                "company_id": COMPANY_ID,
                "session_id": self.session_id,
                "message": self.selected_intent,
                "profile": profile
            }

            start = time.time()
            resp = requests.post(API_URL, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            latency = time.time() - start

            self.sensor.log_event(
                Event.TEXT_INPUT,
                session_id=self.session_id,
                latency_total=latency
            )

            text = data.get("text", "Sem resposta.")
            recs = data.get("recommendations", {})

            self.after(0, lambda: self.render_result(text, recs))

        except Exception as e:
            err = str(e)
            if len(err) > 200:
                err = err[:200] + "..."

            self.after(
                0,
                lambda: self.render_result(
                    f"Erro ao conectar.\n\n{err}",
                    {}
                )
            )

    # QR CODE
    def show_qr(self, recs):
        url = recs.get("link") if isinstance(recs, dict) else None
        if not url:
            return

        qr = qrcode.make(url)
        qr = qr.resize((300, 300))

        img = ImageTk.PhotoImage(qr)

        win = tk.Toplevel(self)
        win.configure(bg="black")

        tk.Label(win, image=img, bg="black").pack(padx=20, pady=20)
        win.image = img

    # SENSOR LOOP
    def poll_presence(self):
        try:
            if self.state == "standby" and self.sensor.should_aware():
                self.on_presence_trigger()
        except Exception as e:
            print("Erro sensor:", e)

        self.after(200, self.poll_presence)

    # CLEANUP
    def on_close(self):
        self.sensor.cleanup()
        self.destroy()


if __name__ == "__main__":
    app = TotemUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()