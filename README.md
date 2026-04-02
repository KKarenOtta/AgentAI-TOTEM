<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

# AgentAI-TOTEM
Desenvolvimento de agentes para um totem interativo com Inteligência Artificial da IA.Gora

###OBS: Modelo arquivo .env

PIR_PIN=17
PRESENCE_HOLD_SECONDS=5
COOLDOWN_SECONDS=10
CAMERA_INDEX=0
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_WARMUP_SECONDS=2.0
JPEG_QUALITY=95
PRESENCE_REQUIRE_IMAGE=true
PRESENCE_REQUIRE_HUMAN_VALIDATION=true

# =========================
# BACKEND LOCAL DO TOTEM
# =========================
TOTEM_ACTIVATE_URL=http://127.0.0.1:8000/totem/activate
TOTEM_INTERACT_URL=http://127.0.0.1:8000/totem/interact
AUDIO_TRANSCRIBE_URL=http://127.0.0.1:8000/api/audio/transcribe
TRACK_API_URL=http://52.201.76.45:8000/api/track

TOTEM_REQUEST_TIMEOUT=30
REQUEST_TIMEOUT_SECONDS=10

# =========================
# STT / TRANSCRIÇÃO
# =========================
AUDIO_TRANSCRIBE_PROVIDER=openai
AUDIO_TRANSCRIBE_LANGUAGE=pt

WHISPER_CPP_BIN=
WHISPER_CPP_MODEL=

LOCAL_WHISPER_MODEL=base
LOCAL_WHISPER_DEVICE=cpu
LOCAL_WHISPER_COMPUTE_TYPE=int8
LOCAL_WHISPER_BEAM_SIZE=1
LOCAL_WHISPER_CPU_THREADS=4

# =========================
# LLM
# =========================
OPENAI_API_KEY="COLOQUE_AQUI"
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_S=45

GEMINI_API_KEY="COLOQUE_AQUI"
GEMINI_MODEL=gemini-2.5-flash

OPENROUTER_API_KEY="COLOQUE_AQUI"
OPENROUTER_MODEL=openrouter/free

HUGGING_FACE_API_KEY="COLOQUE_AQUI"
-------------------------------------------------------

		git pull origin main

		source venv/bin/activate
		
		./venv/bin/python -m pip install --upgrade pip setuptools wheel
		./venv/bin/python -m pip install -r requirements.txt
		./venv/bin/python -m pip install -r requirements-edge.txt

APÓS TRABALHAR NAS SUAS ALTERAÇOES: criar o COMMIT:

		pip freeze > requirements.txt
		pip freeze > requirements-pi.txt
	
		git add .
	
		git commit -m "Descrição das alterações que você realizou”
		
		git push -u origin main


Verifique o status do repositório:
	
		git status


RECARREGAR VARIAVEIS E REINICIAR BACKEND

		pkill -f "uvicorn app.main:app"
		cd ~/AgentAI-TOTEM
		set -a
		source .env
		set +a
		python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

		
		http://192.168.15.12:8000/totem/sim/FLX-001

Endereços de suporte navegador em: 

		http://127.0.0.1:8000/docs
		http://127.0.0.1:8000/openapi.json
		http://127.0.0.1:8000/health
		http://127.0.0.1:8000/totem/sim/FLX-001
		http://127.0.0.1:8000/admin
		http://127.0.0.1:8000/client/FLX-001)


Testar Fluxo completo: 

		cd ~/AgentAI-TOTEM
		set -a
		source .env
		set +a
		cd edge/raspberry_presence_sender
		python3 main.py


Gerar relatórios em CMD:
Relatório resumido
		
		sed -n '1,200p' data/metrics/metrics_report.md

Últimas interações de uma empresa

		grep -n '"company_id": "FLX-001"' data/metrics/metrics.jsonl | tail -n 20

Ver campanhas salvas
		
		cat data/campaigns.json

Ver empresas salvas

		cat data/companies.json
	
