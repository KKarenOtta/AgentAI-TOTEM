<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

# TOTEM I.A.Gora — Plataforma Inteligente de Atendimento com IA Multimodal

O TOTEM I.A.Gora é uma plataforma de atendimento inteligente baseada em IA, projetada para ambientes físicos (white-label).
Ele integra visão computacional, voz, linguagem natural e recomendação inteligente, permitindo interação fluida entre usuários e sistemas digitais.

O sistema utiliza uma arquitetura híbrida com:
	Machine Learning supervisionado (classificação de intenção)
	Busca semântica com embeddings
	Fallback com LLM
	Pipeline automatizado de aprendizado contínuo via Celery

## 1. Stack Principal
	Backend
	Python 3.11
	FastAPI
	Uvicorn
	Machine Learning
	SentenceTransformers (embeddings multilíngue)
	Scikit-learn (Logistic Regression)
	PyTorch (dependência indireta)
	Pipeline / Orquestração
	Celery
	Redis
	Dados
	JSONL / JSON
	Persistência local (estrutura modular)
	Edge (hardware)
	Raspberry Pi 3
	PIR Sensor
	Câmera (fswebcam)

## 2. Arquitetura do Sistema

		      Visão geral
		Usuário (voz/presença)
		        ↓
		Raspberry Pi (sensores + imagem)
		        ↓
		API FastAPI
		        ↓
		Orchestrator
		        ↓
		[1] Intent ML
		[2] FAQ Engine (embedding)
		[3] Contexto empresa
		[4] LLM fallback
		        ↓
		Resposta (voz/texto/UI)
		Pipeline completo (automático)
		Admin altera FAQ
		        ↓
		save_faq()
		        ↓
		Celery (full_pipeline)
		        ↓
		1. build_intent_dataset
		2. train_intent_model
		3. rebuild_embeddings
		4. evaluate
		        ↓
		Modelo atualizado
		        ↓
		Orchestrator usa novo modelo

## 3. Features Utilizadas
	IA e ML
	Classificação de intenção (supervisionado)
	Embeddings semânticos multilíngue
	Re-ranking com score + uso
	Fallback com LLM (OpenAI)
	Sistema
	Cache inteligente
	Pipeline assíncrono
	Aprendizado contínuo
	Multi-empresa (company_id)
	Edge
	Detecção de presença (PIR)
	Captura de imagem
	Validação humana (OpenCV)
	Negócio
	Recomendações
	Cupons (QR Code)
	Tracking de conversão

## 4. Como Rodar o Projeto
	4.1 Setup
	git clone https://github.com/KKarenOtta/AgentAI-TOTEM
	cd ~/Desktop/AgentAI-TOTEM
	
	python3 -m venv venv
	source venv/bin/activate
	
	pip install -r requirements.txt

	Instalar Redis:
	
	brew install redis
	brew services start redis

### 4.2 Testar ambiente
	python - <<'PY'
	from ml.intent.predictor import predict

	print(predict("onde ficam os pinguins?"))
	PY

### 4.3 Rodar aplicação
	Terminal 1 — API
	cd ~/Desktop/AgentAI-TOTEM
	source venv/bin/activate
	uvicorn app.main:app \
	  --host 0.0.0.0 \
	  --port 8000 \
	  --reload \
	  --reload-dir app \
	  --reload-dir core \
	  --reload-dir ml \
	  --reload-dir templates \
	  --reload-dir static

	Terminal 2 - Escutar eventos
		curl -N "http://127.0.0.1:8000/api/events/FLX-001"
	  
	Terminal 3 — Ativar REDIS
		brew services start redis
		TESTAR: redis-cli ping (resposta esperada: PONG)

	 Terminal 4 - Worker Celery
	cd ~/Desktop/AgentAI-TOTEM
	source venv/bin/activate
	celery -A infra.async_tasks.celery_app worker \
 	 --loglevel=info \
  	 --pool=solo

	 Terminal 5 - Testes ML/RN + Pipeline
	 	GERAR DATATSET DE INTENÇAO
			cd ~/Desktop/AgentAI-TOTEM
			source venv/bin/activate
			python ml/intent/dataset_builder.py
			wc -l data/ml/intent/dataset.jsonl
			head data/ml/intent/dataset.jsonl

		TREINAR MODELO MANUAL
			python ml/intent/train.py
		
		TESTAR INFERENCIA
			python - <<'PY'
			from ml.intent.predictor import predict
			tests = [
			    "onde ficam os pinguins?",
			    "que horas fecha?",
			    "tem desconto hoje?",
			    "onde comer?",
			    "tem banheiro?",
			    "onde ficam as flores?"
			]
			for t in tests:
			    intent, conf = predict(t)
			    print(t, "=>", intent, conf)
			PY
		
		DISPARAR PIPELINE COMPLETA (CELERY)
			python - <<'PY'
			from infra.async_tasks.tasks import full_pipeline
			result = full_pipeline.delay()
			print("task_id:", result.id)
			PY

		VER RELATORIO DO MODELO
			cat data/ml/intent/reports/training_report.json
		
	Abrir acessos no navegador
	Usuário (Totem)
	http://127.0.0.1:8000/totem/FLX-001
	Admin/Empresa
	http://127.0.0.1:8000/login
	- acesso: admin | senha: 123456
			  flx   | senha: flz123
			  
	 Terminal 6 - acesso [raspberry]
			arp -a
			ssh lostgear@raspberrypi.local
			Confirmar hostname -I
			ping 192.168.15.12
			senha: ****
			cd AgentAI-TOTEM
			source venv/bin/activate

	Terminal 7 - [raspberry]
			SUBIR SERVIDOR DE VOZ:
				cd ~/AgentAI-TOTEM
				source venv/bin/activate	
				python edge/voice_server.py

	Terminal 8 - [raspberry]
				cd ~/AgentAI-TOTEM
				source venv/bin/activate
				which python
				which python3
				python -c "import flask; print(flask.__version__)"
				
				cd alpha_test
				python app.py

				Navegador: http://192.168.15.15:5000/
				

## 5. Métricas Utilizadas
	ML (Intent)
	Accuracy
	Precision (macro / weighted)
	Recall
	F1-score
	Sistema
	Tempo de resposta
	Cache hit rate
	Confidence do modelo
	Negócio
	Taxa de conversão (cupons)
	Engajamento
	Uso por intent

## 6. Análise
	Resultado atual
		accuracy: ~0.69
		macro_f1: ~0.70
	Interpretação
		Modelo funcional e consistente
	Limitação principal: 
		Dataset pequeno
		Confiança baixa em classes similares
		Dependência de dados reais para evolução

## 7. Conclusão

O AgentAI-TOTEM apresenta um sistema baseado em regras para uma plataforma de IA híbrida com:

	ML + Embeddings + Regras + LLM + Feedback

Capaz de:
	
	Aprender com uso real
	Melhorar continuamente
	Escalar para múltiplas empresas
	Operar em tempo real em ambiente físico
	
