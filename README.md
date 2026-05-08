<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

# TOTEM I.A.Gora — Enterprise AI Multimodal Platform

O TOTEM I.A.Gora é uma plataforma enterprise de atendimento inteligente baseada em IA multimodal, projetada para ambientes físicos, varejo, zoológicos, shoppings, eventos, hospitais, turismo e operações white-label.

A plataforma integra:

- IA Conversacional
- Visão Computacional
- Processamento de Voz
- Busca Semântica
- Recommendation Engine
- Sentiment Analysis
- Reward Learning
- Edge Computing
- Analytics Enterprise
- Persistência híbrida JSON + AWS RDS

---

# 1. Arquitetura Enterprise

## Fluxo operacional completo

			     Sensores Raspberry Pi 3
				(3 sensores ultrassônicos)
				            ↓
				Detecção contínua de presença
				       (5 segundos)
				            ↓
					Captura de imagem
					(fswebcam / OpenCV)
				            ↓
					Validação humana
					(OpenCV + AWS Rekognition)
				            ↓
					Trigger do TOTEM
				            ↓
					Greeting automático
					(TTS + animação UI)
				            ↓
				Captura de voz do usuário
				            ↓
					STT (Speech-to-Text)
				            ↓
					Pipeline de IA
					 ├── Intent ML
					 ├── FAQ Semântica
					 ├── Embeddings
					 ├── Contexto da empresa
					 ├── Recommendation Engine
					 ├── Sentiment Analysis
					 └── LLM Fallback
					        ↓
					Resposta inteligente
				            ↓
						TTS + UI
				            ↓
				QR Code / Device Handoff
				            ↓
				  Lead Capture + LGPD
				            ↓
					NPS + Analytics
				            ↓
					Reward Learning
				            ↓
				  Aprendizado contínuo

# 2. Stack Tecnológica
   
		Backend
		Python 3.11
		FastAPI
		Uvicorn
		Jinja2
		SQLAlchemy
		IA / Machine Learning
		SentenceTransformers
		Transformers
		HuggingFace
		Scikit-Learn
		PyTorch
		OpenAI API
		Embeddings multilíngue
		Pipeline / Runtime
		Celery
		Redis
		Celery Beat
		Sync Worker
		Runtime Manager
		Banco de Dados
		Persistência híbrida
		JSONL local resiliente
		JSON local
		AWS PostgreSQL RDS
		Sync automático
		Edge AI
		Raspberry Pi 3
		Sensores ultrassônicos
		OpenCV
		fswebcam
		Captura de áudio
		Voice Server

# 3. Arquitetura de IA
## 3.1 Intent Classification

Classificação supervisionada de intenção usando Scikit-Learn.

Exemplos:
	localização
	horário
	promoção
	alimentação
	banheiro
	eventos
	suporte

## 3.2 FAQ Engine Semântica

Sistema baseado em embeddings semânticos multilíngue.

		 Pergunta usuário
		        ↓
		    Embedding
		        ↓
		 Busca vetorial
		        ↓
		Ranking semântico
		        ↓
		   Resposta FAQ

Possui:

	semantic ranking
	usage learning
	correction workflow
	reindexação automática
	monitoramento de qualidade

## 3.3 LLM Fallback

Quando a FAQ não encontra resposta satisfatória:

	FAQ score baixo
	        ↓
	Fallback OpenAI
	        ↓
	Resposta gerada
	        ↓
	Persistência para aprendizado

## 3.4 Sentiment Analysis

Análise emocional utilizando Transformers.

Classificações: positive - neutral - negative

Também calcula:
	promoter
	passive
	detractor
	frustration risk
	engagement score
Integrado ao NPS.

## 3.5 Recommendation Engine

Sistema inteligente de campanhas. Possui:

	recommendation scoring
	reward learning
	CTR analytics
	conversion analytics
	adaptive campaign weights

Eventos:

	impression
	click
	conversion
	redeemed
	interaction

# 4. Persistência Enterprise
## 4.1 Persistência Local

Arquivos:

	data/
	├── analytics/
	├── faq/
	├── leads/
	├── lgpd/
	├── metrics/
	├── recommendation_feedback/
	├── reports/
	├── semantic/
	├── sentiment/
	└── sync/

## 4.2 AWS RDS

O sistema sincroniza automaticamente:

	leads
	métricas
	consentimentos
	analytics
	sync audit

Fluxo:

	JSONL local
	      ↓
	Sync Queue
	      ↓
	Sync Worker
	      ↓
	AWS RDS PostgreSQL

#5. Runtime Enterprise
Inicialização única

O sistema possui runtime centralizado.

Comando:

	bash runtime/totem_manager.sh restart

O runtime sobe automaticamente:

Backend FastAPI
Redis validation
Celery Worker
Celery Beat
Sync Worker
Healthcheck
AWS validation

# 6. Como Rodar o Projeto
## 6.1 Setup

	git clone https://github.com/KKarenOtta/AgentAI-TOTEM

	cd ~/Desktop/AgentAI-TOTEM

	python3 -m venv venv

	source venv/bin/activate

	pip install -r requirements.txt/ requirements-edge.txt

6.2 Redis

macOS:
	
	brew install redis
	
	brew services start redis

	redis-cli ping

Resposta esperada:

	PONG

## 6.3 Runtime único
	bash runtime/totem_manager.sh restart
## 6.4 Verificar status
	bash runtime/totem_manager.sh status
## 6.5 Ver logs
	bash runtime/totem_manager.sh logs

# 7. Raspberry Pi Runtime
## 7.1 Runtime sensores
	cd ~/AgentAI-TOTEM
	
	source venv/bin/activate

	python edge/raspberry_runtime/sensor_runtime.py

## 7.2 Voice Server
	cd ~/AgentAI-TOTEM
	
	source venv/bin/activate
	
	python edge/voice_server.py

# 8. Interfaces do Sistema - navegador

Totem
	
	http://52.201.76.45:8000/totem/FLX-001

Login
	
	http://52.201.76.45:8000/login

Dashboard empresa
	
	http://52.201.76.45:8000/client/FLX-001

FAQ Admin
	
	http://52.201.76.45:8000/admin/faq

# 9. Dashboard Enterprise

	KPIs operacionais
	sentiment analytics
	reward learning
	campaign analytics
	sync health
	NPS analytics
	AI metrics
	conversion analytics
	realtime status

# 10. Relatórios Enterprise

O sistema gera relatórios PDF automáticos.

Inclui:

	KPIs
	campanhas
	sentiment analysis
	analytics temporal
	reward learning
	métricas IA
	NPS
	performance operacional

API:

	POST /api/reports/{company_id}/generate
	GET  /api/reports/{company_id}/latest

# 11. Pipeline de Aprendizado Contínuo
	Celery Pipeline
	Admin corrige FAQ
	        ↓
	save_faq()
	        ↓
	reindex embeddings
	        ↓
	dataset builder
	        ↓
	fine tune
	        ↓
	evaluate
	        ↓
	optimize
	        ↓
	modelo atualizado

# 12. Métricas
	IA
	Accuracy
	Precision
	Recall
	F1-score
	Semantic hit rate
	Fallback rate
	Confidence score
	Operacional
	Latência
	Sync health
	Queue status
	Runtime health
	Negócio
	CTR
	Conversion rate
	Reward score
	Leads
	NPS
	Engagement

# 13. Estrutura Principal
	app/
	core/
	DB/
	edge/
	infra/
	ml/
	recommender/
	runtime/
	templates/
	static/
	data/

# 14. Estado Atual do Projeto - O TOTEM atualmente possui:

	IA multimodal funcional
	aprendizado contínuo
	analytics enterprise
	reward learning
	recommendation engine
	sentiment analysis
	embeddings persistentes
	runtime centralizado
	persistência híbrida
	dashboard enterprise
	geração de relatórios
	edge orchestration
	integração AWS
	multi-tenant

# 15. Roadmap Enterprise

Próximas evoluções:

Feature Store
Vector Database dedicado
Distributed Event Bus
Online Learning
Fine-tuning contínuo
Multi-node orchestration
Voice streaming
Interrupção de voz
Agent memory
RLHF
Observability
Distributed tracing
GPU inference
Multi-tenant vector isolation

16. Conclusão

O TOTEM I.A.Gora evoluiu de um protótipo baseado em regras para uma plataforma enterprise de IA multimodal com:

						ML + Embeddings + Reward Learning + LLM + Analytics + Edge AI

Capaz de:

operar em tempo real
aprender continuamente
integrar sensores físicos
gerar inteligência operacional
escalar multi-empresa
executar analytics enterprise
entregar atendimento inteligente em ambientes físicos
MD

python -m py_compile app/main.py

git status --short
