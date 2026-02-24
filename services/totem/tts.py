import io, time, requests
import soundfile as sf
from gtts import gTTS
from services.realtime.event_bus import publish

def gerar_audio(texto: str, idioma="pt", hugging_key: str | None = None):
    idiomas_suportados = {
        "pt": ("Português", "facebook/mms-tts-por"),
        "en": ("Inglês", "facebook/mms-tts-eng"),
        "es": ("Espanhol", "facebook/mms-tts-spa"),
    }

    if idioma not in idiomas_suportados:
        idioma = "pt"

    _, modelo_voz = idiomas_suportados[idioma]
    hf_status_code = None
    hf_err_text = None

    # Hugging Face (voz neural)
    if hugging_key:
        try:
            API_URL = f"https://router.huggingface.co/hf-inference/models/{modelo_voz}"
            headers = {
                "Authorization": f"Bearer {hugging_key}",
                "Accept": "audio/wav",
                "Content-Type": "application/json",
            }
            payload = {"inputs": texto}

            t0 = time.perf_counter()
            r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            t1 = time.perf_counter()
            hf_latency = round((t1 - t0), 3)

            hf_status_code = r.status_code
            if r.status_code == 200:
                audio_bytes = io.BytesIO(r.content)
                data, samplerate = sf.read(audio_bytes)
                out_path = "data/metrics/voz_hf.wav"
                sf.write(out_path, data, samplerate)
                return out_path, "huggingface", hf_status_code, None, hf_latency
            else:
                hf_err_text = (r.text or "")[:800]
        except Exception as e:
            hf_err_text = str(e)

    # fallback gTTS
    t0 = time.perf_counter()
    lang_map = {"pt": "pt", "en": "en", "es": "es"}
    lang_final = lang_map.get(idioma, "pt")
    tts = gTTS(text=texto, lang=lang_final)
    out_path = "data/metrics/voz_fallback.mp3"
    tts.save(out_path)
    t1 = time.perf_counter()
    gtts_latency = round((t1 - t0), 3)

    # Real-time metrics
    event = {
        "type": "totem_interaction",
        "timestamp": metric["timestamp"],
        "company_id": company_id,
        "session_id": session_id,
        "profile": profile,
        "question": pergunta,
        "response": resposta,
        "recommendations": recs,
        "latency": {"gen": gen_latency, "tts": tts_latency},
    }
    publish(company_id, event)

    return out_path, "gTTS", hf_status_code, hf_err_text, gtts_latency