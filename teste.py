!pip install gTTS

!pip install -U torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
               transformers==4.46.2 soundfile==0.12.1 langdetect==1.0.9 \
               google-generativeai==0.7.2 protobuf==4.25.3 --quiet

!pip install -U transformers==4.46.2 huggingface_hub==0.34.4 --quiet





from datetime import datetime
import time, json, requests, soundfile as sf, io, os
from IPython.display import Audio, display, Markdown
import google.generativeai as genai
from google.colab import userdata
from langdetect import detect
from gtts import gTTS
import pandas as pd



gemini_key = userdata.get("GEMINI_API_KEY_1")
hugging_key = userdata.get("HUGGING_FACE")

if not gemini_key:
    raise ValueError("Configure GEMINI_API_KEY_1 em Colab > Chave/Secrets")
if not hugging_key:
    print("Configure HUGGING_FACE_KEY em Colab > Chave/Secrets")

genai.configure(api_key=gemini_key)
model = genai.GenerativeModel("models/gemini-2.5-pro")

# DADOS DA INTERAÇAO
METRICS_JSONL = "metrics.jsonl"
METRICS_CSV  = "metrics.csv"
REPORT_MD    = "metrics_report.md"

if not os.path.exists(METRICS_JSONL):
    open(METRICS_JSONL, "w").close()

def save_metric(entry: dict):
    entry_json = json.dumps(entry, ensure_ascii=False)
    with open(METRICS_JSONL, "a", encoding="utf-8") as f:
        f.write(entry_json + "\n")
    with open(METRICS_JSONL, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(METRICS_CSV, index=False, encoding="utf-8-sig")


# GERAR AUDIO
def gerar_audio(texto: str, idioma="pt", hugging_key=None):
    idiomas_suportados = {
        "pt": ("Português", "facebook/mms-tts-por"),
        "en": ("Inglês", "facebook/mms-tts-eng"),
        "es": ("Espanhol", "facebook/mms-tts-spa"),
    }

    if idioma not in idiomas_suportados:
        print(f"Idioma '{idioma}' não suportado, usarei o português por padrão.")
        idioma = "pt"

    idioma_nome, modelo_voz = idiomas_suportados[idioma]

    # Inicia valores para métricas
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

            # Contagem tempo - request
            t0 = time.perf_counter()
            r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            t1 = time.perf_counter()
            hf_latency = round((t1 - t0), 3)

            hf_status_code = r.status_code
            if r.status_code == 200:
                audio_bytes = io.BytesIO(r.content)
                data, samplerate = sf.read(audio_bytes)
                out_path = "voz_hf.wav"
                sf.write(out_path, data, samplerate)
                return out_path, "huggingface", hf_status_code, None, hf_latency
            else:
                hf_err_text = (r.text or "")[:800]
                print(f"Erro API Hugging Face {r.status_code}: {hf_err_text[:200]}")
        except Exception as e:
            hf_err_text = str(e)
            print(f"Erro do Hugging Face: {e}")

    # Caso a voz natural falhe: Recurso de Fallback (gTTS - GEMINI)
    try:
        t0 = time.perf_counter()
        lang_map = {"pt": "pt", "en": "en", "es": "es"}
        lang_final = lang_map.get(idioma, "pt")
        tts = gTTS(text=texto, lang=lang_final)
        out_path = "voz_fallback.mp3"
        tts.save(out_path)
        t1 = time.perf_counter()
        gtts_latency = round((t1 - t0), 3)
        return out_path, "gTTS", hf_status_code, hf_err_text, gtts_latency
    except Exception as e:
        raise RuntimeError(f"Erro ao gerar qualquer resposta de voz: {e}")


### Minha função XUXU : GERA RESPOSTA, DADOS E FALA!!! ###
def resposta_totem(pergunta: str, save_metrics=True, show_report=True):
    interaction_start = datetime.now()
    timestamp_iso = interaction_start.isoformat(timespec="seconds")

    try:
        idioma = detect(pergunta)
    except:
        idioma = "pt"
    if idioma not in ["pt", "en", "es"]:
        idioma = "pt"

    idiomas = {"pt": "Português", "en": "Inglês", "es": "Espanhol"}


    # Horário conforme componente RTC (ISO)
    data_hora = interaction_start.strftime("%d/%m/%Y (%A), %H:%M")
    prompt = (
        f"Agora são {data_hora}. "
        f"Responda em {idiomas.get(idioma, 'Português')}. "
        f"Pergunta: {pergunta}"
    )

    # Gera resposta GEMINI e mede latência
    t0 = time.perf_counter()
    resposta = model.generate_content(prompt).text.strip()
    t1 = time.perf_counter()
    gen_latency = round((t1 - t0), 3)

    # Gera voz (Hugging Face ou fallback gTTS)
    audio_t0 = time.perf_counter()
    audio_path, voice_source, hf_status, hf_err, tts_latency = gerar_audio(resposta, idioma, hugging_key)
    audio_t1 = time.perf_counter()
    total_audio_latency = round((audio_t1 - audio_t0), 3)

    # Reproduz áudio no computador (autofalantes)
    display(Audio(audio_path, autoplay=True))

    # Dados
    metric = {
        "timestamp": timestamp_iso,
        "question": pergunta,
        "response": resposta,
        "language_detected": idioma,
        "language_name": idiomas.get(idioma, "Português"),
        "voice_source": voice_source,
        "audio_file": audio_path,
        "gen_latency_s": gen_latency,
        "tts_latency_s": tts_latency,
        "total_audio_time_s": total_audio_latency,
        "hf_status_code": hf_status,
        "hf_error": hf_err,
    }

    if save_metrics:
        save_metric(metric)

    if show_report:
        if os.path.exists(METRICS_CSV):
            df = pd.read_csv(METRICS_CSV)
        else:
            df = pd.DataFrame([metric])

        total_interactions = len(df)
        last = df.iloc[-1].to_dict()
        counts_by_voice = df["voice_source"].value_counts().to_dict() if "voice_source" in df.columns else {}

        md = f"""
          ### Relatório Totem I.A.Gora
          - Total de interações: {total_interactions}
          - Última interação: {metric['timestamp']}
          - Pergunta: {metric['question']}
          - Resposta: {metric['response']}
          - Voz usada: {metric['voice_source']}
          - Distribuição de TTS: {counts_by_voice}
        """

        with open(REPORT_MD, "w", encoding="utf-8") as f:
            f.write(md)

        display(Markdown(md))
        display(df.tail(10))


    return metric


pergunta = input("Digite sua pergunta: ")
metric = resposta_totem(pergunta)

print("Métrica salva: ")
print(json.dumps(metric, ensure_ascii=False, indent=2))
print(f"Arquivos gerados: {METRICS_JSONL}, {METRICS_CSV}, {REPORT_MD if os.path.exists(REPORT_MD) else '(sem arquivo de relatório)'}")