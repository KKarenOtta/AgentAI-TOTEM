import os
import time
import json
import uuid
import threading
import requests
from dotenv import load_dotenv

import qrcode
from PIL import ImageTk
import tkinter as tk

load_dotenv()

TOTEM_API = os.getenv("TOTEM_API_URL", "http://localhost:9000/totem/interact")
TRACK_API = os.getenv("TRACK_API_URL", "http://localhost:9000/api/track")

COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")
PREFER_AUDIO = os.getenv("PREFER_AUDIO", "true").lower() == "true"

from sensors.pi_totem_sensor import SensorHub, Event


AGE_OPTIONS = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

INTENT_OPTIONS = [
    ("Promoções", "Quais promoções estão ativas para mim hoje?"),
    ("Produtos", "Me recomende produtos/ofertas ideais para mim hoje."),
    ("Suporte", "Preciso de ajuda/atendimento. Como posso resolver?"),
]


def call_backend(message: str, profile: dict, session_id: str):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": session_id,
        "message": message,
        "prefer_audio": PREFER_AUDIO,
        "profile": profile,
    }
    r = requests.post(TOTEM_API, json=payload, timeout=(5, 15))
    r.raise_for_status()
    return r.json()


class TotemApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Totem I.A.Gora - Raspberry Pi (MTM-3201)")
        self.attributes("-fullscreen", True)
        self.configure(bg="black")

        self.hub = SensorHub()

        self.state = "standby"
        self.selected_age = None
        self.selected_intent = None
        self.session_id = None
        self.current_response = None

        self.container = tk.Frame(self, bg="black")
        self.container.pack(fill="both", expand=True)

        self.header = tk.Label(
            self.container,
            text="Totem I.A.Gora",
            font=("Arial", 30, "bold"),
            fg="#00ff99",
            bg="black"
        )
        self.header.pack(pady=20)

        self.content = tk.Frame(self.container, bg="black")
        self.content.pack(fill="both", expand=True)

        self.footer = tk.Label(
            self.container,
            text="",
            font=("Arial", 14),
            fg="#aaaaaa",
            bg="black"
        )
        self.footer.pack(pady=10)

        self.bind("<Escape>", lambda e: self.quit_app())
        self.bind("w", lambda e: self.on_wakeword())
        self.bind("W", lambda e: self.on_wakeword())

        self.render_standby()
        self.after(200, self.poll_presence)

    def new_session_id(self):
        return f"sess-{uuid.uuid4().hex[:8]}"

    def update_footer(self, extra_text: str = ""):
        base = f"Empresa: {COMPANY_ID} | Sessão: {self.session_id or '-'} | API: {TOTEM_API}"
        if extra_text:
            base = f"{base} | {extra_text}"
        self.footer.configure(text=base)

    def quit_app(self):
        try:
            self.hub.cleanup()
        except Exception:
            pass
        self.destroy()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def render_standby(self):
        self.state = "standby"
        self.selected_age = None
        self.selected_intent = None
        self.current_response = None
        self.clear_content()

        label = tk.Label(
            self.content,
            text="Aproxime-se para iniciar\n(presença contínua por 3 segundos)",
            font=("Arial", 40, "bold"),
            fg="white",
            bg="black",
            justify="center"
        )
        label.pack(expand=True)

        hint = tk.Label(
            self.content,
            text="Pressione W para simular wakeword",
            font=("Arial", 18),
            fg="#aaaaaa",
            bg="black"
        )
        hint.pack(pady=20)

        self.update_footer("modo: standby")

    def render_age_question(self):
        self.state = "age"
        self.clear_content()

        label = tk.Label(
            self.content,
            text="Selecione sua faixa etária:",
            font=("Arial", 34, "bold"),
            fg="white",
            bg="black"
        )
        label.pack(pady=20)

        grid = tk.Frame(self.content, bg="black")
        grid.pack(pady=10)

        for idx, age in enumerate(AGE_OPTIONS):
            btn = tk.Button(
                grid,
                text=age,
                font=("Arial", 28, "bold"),
                width=8,
                height=2,
                bg="#1f1f1f",
                fg="white",
                activebackground="#00ff99",
                activeforeground="black",
                command=lambda a=age: self.on_age_selected(a)
            )
            row = idx // 4
            col = idx % 4
            btn.grid(row=row, column=col, padx=10, pady=10)

        back = tk.Button(
            self.content,
            text="Voltar",
            font=("Arial", 20),
            bg="#333",
            fg="white",
            command=self.render_standby
        )
        back.pack(pady=20)

        self.update_footer("modo: seleção de idade")

    def render_intent_question(self):
        self.state = "intent"
        self.clear_content()

        label = tk.Label(
            self.content,
            text="O que você procura hoje?",
            font=("Arial", 34, "bold"),
            fg="white",
            bg="black"
        )
        label.pack(pady=20)

        for title, msg in INTENT_OPTIONS:
            btn = tk.Button(
                self.content,
                text=title,
                font=("Arial", 28, "bold"),
                width=20,
                height=2,
                bg="#1f1f1f",
                fg="white",
                activebackground="#00ff99",
                activeforeground="black",
                command=lambda m=msg: self.on_intent_selected(m)
            )
            btn.pack(pady=10)

        back = tk.Button(
            self.content,
            text="Voltar",
            font=("Arial", 20),
            bg="#333",
            fg="white",
            command=self.render_age_question
        )
        back.pack(pady=20)

        self.update_footer("modo: seleção de intenção")

    def render_processing(self):
        self.state = "processing"
        self.clear_content()

        label = tk.Label(
            self.content,
            text="Processando...",
            font=("Arial", 40, "bold"),
            fg="#ffcc00",
            bg="black"
        )
        label.pack(expand=True)

        self.update_footer("modo: processamento")

    def render_result(self, text: str, recs: dict):
        self.state = "result"
        self.clear_content()

        title = tk.Label(
            self.content,
            text="Resultado",
            font=("Arial", 34, "bold"),
            fg="#00ff99",
            bg="black"
        )
        title.pack(pady=10)

        txt = tk.Text(
            self.content,
            wrap="word",
            font=("Arial", 22),
            height=10,
            bg="#111",
            fg="white"
        )
        txt.insert("1.0", text or "Nenhuma resposta textual recebida.")
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=30, pady=10)

        rec_title = tk.Label(
            self.content,
            text="Sugestões:",
            font=("Arial", 26, "bold"),
            fg="white",
            bg="black"
        )
        rec_title.pack(pady=5)

        actions = (recs or {}).get("top_actions", []) or []

        rec_box = tk.Text(
            self.content,
            wrap="word",
            font=("Arial", 18),
            height=6,
            bg="#111",
            fg="white"
        )

        for action in actions[:5]:
            if isinstance(action, dict):
                rec_box.insert("end", f"• {action.get('action')} ({action.get('why')})\n")
            else:
                rec_box.insert("end", f"• {action}\n")

        if not actions:
            rec_box.insert("end", "• Nenhuma sugestão disponível.\n")

        rec_box.configure(state="disabled")
        rec_box.pack(fill="x", padx=30, pady=10)

        primary_action = actions[0] if actions else {"action": "Quero uma recomendação", "why": ""}

        want_btn = tk.Button(
            self.content,
            text="Quero essa oferta",
            font=("Arial", 24, "bold"),
            bg="#00ff99",
            fg="black",
            width=22,
            height=2,
            command=lambda: self.track_and_show_qr(primary_action, campaign_id=None)
        )
        want_btn.pack(pady=10)

        btn_frame = tk.Frame(self.content, bg="black")
        btn_frame.pack(pady=20)

        restart = tk.Button(
            btn_frame,
            text="Nova interação",
            font=("Arial", 20, "bold"),
            bg="#00ff99",
            fg="black",
            width=16,
            height=2,
            command=self.render_standby
        )
        restart.grid(row=0, column=0, padx=10)

        close = tk.Button(
            btn_frame,
            text="Encerrar",
            font=("Arial", 20),
            bg="#333",
            fg="white",
            width=16,
            height=2,
            command=self.quit_app
        )
        close.grid(row=0, column=1, padx=10)

        self.update_footer("modo: resultado")

    def track_and_show_qr(self, action: dict, campaign_id: str | None = None):
        action_label = action.get("action") if isinstance(action, dict) else str(action)
        action_id = (
            action.get("id") if isinstance(action, dict) else None
        ) or action_label.lower().replace(" ", "_")[:32]

        payload = {
            "company_id": COMPANY_ID,
            "session_id": self.session_id,
            "event": "action_click",
            "action_id": action_id,
            "action_label": action_label,
            "campaign_id": campaign_id,
            "turn_index": None,
            "message_id": None,
            "meta": {"source": "touchscreen", "device": "MTM-3201"},
        }

        try:
            requests.post(TRACK_API, json=payload, timeout=(3, 8)).raise_for_status()
        except Exception as e:
            self.update_footer(f"Falha ao registrar track: {e}")

        qr_content = json.dumps(
            {
                "company_id": COMPANY_ID,
                "session_id": self.session_id,
                "action_id": action_id,
                "action_label": action_label,
                "campaign_id": campaign_id,
                "ts": int(time.time())
            },
            ensure_ascii=False
        )

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        tk_img = ImageTk.PhotoImage(img)

        win = tk.Toplevel(self)
        win.configure(bg="black")
        win.attributes("-fullscreen", True)

        title = tk.Label(
            win,
            text="Escaneie para resgatar",
            font=("Arial", 32, "bold"),
            fg="#00ff99",
            bg="black"
        )
        title.pack(pady=20)

        lbl = tk.Label(win, image=tk_img, bg="black")
        lbl.image = tk_img
        lbl.pack(pady=10)

        sub = tk.Label(
            win,
            text=action_label,
            font=("Arial", 20),
            fg="white",
            bg="black",
            wraplength=900,
            justify="center"
        )
        sub.pack(pady=10)

        btn = tk.Button(
            win,
            text="Voltar",
            font=("Arial", 22, "bold"),
            bg="#00ff99",
            fg="black",
            width=12,
            command=win.destroy
        )
        btn.pack(pady=20)

    def on_presence_trigger(self):
        if not self.session_id:
            self.session_id = self.new_session_id()
        self.render_age_question()

    def on_age_selected(self, age_range: str):
        self.selected_age = age_range
        self.render_intent_question()

    def on_wakeword(self):
        temp, hum = self.hub.read_env()

        if not self.session_id:
            self.session_id = self.new_session_id()

        self.hub.log_event(
            Event.WAKEWORD,
            dist=None,
            temp=temp,
            hum=hum,
            session_id=self.session_id,
            extra={
                "source": "keyboard_W",
                "presence_mode": "pir_confirmed_3s"
            }
        )

        if self.state == "standby":
            self.on_presence_trigger()

    def on_intent_selected(self, message: str):
        self.selected_intent = message
        self.render_processing()

        thread = threading.Thread(target=self._backend_flow, daemon=True)
        thread.start()

    def _backend_flow(self):
        temp, hum = self.hub.read_env()
        rtc_iso = self.hub.read_timestamp()

        self.hub.log_event(
            Event.TEXT_INPUT,
            dist=None,
            temp=temp,
            hum=hum,
            session_id=self.session_id,
            extra={
                "message": self.selected_intent,
                "age_range": self.selected_age,
                "prefer_audio": PREFER_AUDIO,
                "input_mode": "touchscreen",
                "presence_mode": "pir_confirmed_3s",
            }
        )

        self.hub.log_event(
            Event.SESSION_START,
            dist=None,
            temp=temp,
            hum=hum,
            session_id=self.session_id,
            extra={"ui_state": "processing"}
        )

        profile = {
            "age_range": self.selected_age,
            "gender": "unknown",
            "confidence": None,
            "segment": "new_visitor",
            "device": "totem_rpi3",
            "locale": "pt-BR",
            "extra": {
                "temp_c": temp,
                "humidity_pct": hum,
                "rtc_iso": rtc_iso,
                "presence_mode": "pir_confirmed_3s",
                "pir_detected": True,
                "camera_source": "MTM-3201",
                "totem_model": "MTM-3201",
            }
        }

        t0 = time.time()
        latency_llm = None
        latency_tts = None

        try:
            resp = call_backend(self.selected_intent, profile, self.session_id)
            latency_total = time.time() - t0

            metrics = resp.get("metrics") or {}
            latency_llm = metrics.get("latency_llm_s") or metrics.get("gen_latency_s")
            latency_tts = metrics.get("latency_tts_s") or metrics.get("tts_latency_s")

            text = resp.get("text", "")
            recs = resp.get("recommendations", {})

            top_actions = (recs or {}).get("top_actions") or []

            self.hub.log_event(
                Event.SESSION_END,
                dist=None,
                temp=temp,
                hum=hum,
                session_id=self.session_id,
                latency_total=latency_total,
                latency_llm=latency_llm,
                latency_tts=latency_tts,
                extra={
                    "backend_ok": True,
                    "backend_status_code": 200,
                    "language": resp.get("language"),
                    "recs_count": len(top_actions),
                    "audio_file": resp.get("audio_file"),
                }
            )

            self.after(0, lambda: self.render_result(text, recs))

        except Exception as e:
            latency_total = time.time() - t0

            self.hub.log_event(
                Event.SESSION_END,
                dist=None,
                temp=temp,
                hum=hum,
                session_id=self.session_id,
                latency_total=latency_total,
                latency_llm=latency_llm,
                latency_tts=latency_tts,
                extra={
                    "backend_ok": False,
                    "backend_status_code": None,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

            self.after(
                0,
                lambda: self.render_result(
                    f"Erro ao conectar no servidor.\n\nDetalhes: {e}",
                    {}
                )
            )

    def poll_presence(self):
        try:
            if self.state == "standby" and self.hub.should_aware():
                self.session_id = self.new_session_id()
                temp, hum = self.hub.read_env()

                self.hub.log_event(
                    Event.AWARE,
                    dist=None,
                    temp=temp,
                    hum=hum,
                    session_id=self.session_id,
                    extra={
                        "rule": "pir_presence_3s",
                        "presence_mode": "pir_confirmed_3s",
                    }
                )
                self.on_presence_trigger()

        except Exception as e:
            self.update_footer(f"Erro de presença: {e}")

        self.after(200, self.poll_presence)


if __name__ == "__main__":
    app = TotemApp()
    app.mainloop()