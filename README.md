<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

# AgentAI-TOTEM
Desenvolvimento de agentes para um totem interativo com Inteligência Artificial da IA.Gora

INSTRUÇOES GIT: 
CLONAR repositório: 

		git clone https://github.com/KKarenOtta/AgentAI-TOTEM.git

CRIAR UMA PASTA na sua máquina e uma BRANCH: Antes de fazer alterações, cada membro deve criar um branch para suas alterações. Isso ajuda a manter o histórico do projeto limpo e organizado.

		cd 	AgentAI-TOTEM

		git checkout -b nome-do-branch

		code .

###OBS: cada usuário deverá criar sua pasta .env incluindo suas chaves secretas para as contas: 
	As pastas já estão protegidas pelo arquivo gitignore.

	OPENAI_API_KEY=
	GEMINI_API_KEY=
	OPENROUTER_API_KEY=
	HUGGING_FACE= (LLM: se nenhuma chave de LLM estiver definida, o sistema opera em modo fallback/demo)
	APP_NAME=AgentAI-TOTEM
	APP_ENV=development
	LOG_LEVEL=INFO
	HOST=127.0.0.1
	PORT=9000
	DEFAULT_COMPANY_ID=FLX-001
	PRESENCE_TIMEOUT_S=15
	TOTEM_API_URL=http://127.0.0.1:9000/api
	COMPANY_ID=FLX-001
	DEVICE_ID=RPI3-PIR-001
	PIR_PIN=17
	POLL_INTERVAL_S=0.20
	CLEAR_DELAY_S=4


APÓS TRABALHAR NAS SUAS ALTERAÇOES: criar o COMMIT:

		pip freeze > requirements.txt
		pip freeze > requirements-pi.txt
	
		git add .
	
		git commit -m "Descrição das alterações que você realizou”

antes de fazer o push, é uma boa prática puxar as últimas alterações de branch principal para evitar conflitos: 
		
		git pull origin main
		
		git push -u origin nome-do-branch


Atualizar o Branch Local
Após a mesclagem, cada membro deve atualizar seu branch local para garantir que está trabalhando com a versão mais recente:
	
		git checkout main
		
		git pull origin main


+++ DIA-A-DIA: Antes de iniciar o trabalho diário em seu projeto, é importante garantir que você esteja trabalhando com a versão mais recente do código. Aqui está um passo a passo para atualizar seu projeto e continuar:
Entre na sua pasta de projeto da sua máquina:
	ex: cd "/Users/karenota/Desktop/AgentAI-TOTEM”

Ative seu ambiente virtual: 

		python3.11 -m venv venv
		source venv/bin/activate

Atualize sua branch principal:
		
		git checkout main

Puxe as últimas alterações do repositório remoto:
		
		git pull origin main
		./venv/bin/python -m pip install --upgrade pip setuptools wheel
		./venv/bin/python -m pip install -r requirements.txt
		
Verifique o status do repositório:
	
		git status

Se houver alterações não comitadas, você pode querer fazer um commit ou stash delas antes de continuar.

Continue seu Trabalho: Agora você pode mudar para o branch onde estava trabalhando ou criar um novo branch para suas alterações:
	  
		git checkout -b nome-do-branch

Para verificar os templates localmente:
	Certifique-se de estar com o venv ativado!

		./venv/bin/python -m uvicorn app.main:app \
		  --host 127.0.0.1 \
		  --port 9000 \
		  --reload \
		  --reload-dir app \
		  --reload-dir services \
		  --reload-dir agents \
		  --reload-dir repositories \
		  --reload-dir templates \
		  --reload-dir static \
		  --reload-exclude 'venv/*'

Abrir navegador em: 

		http://127.0.0.1:9000/ → página inicial
		http://127.0.0.1:9000/docs → Swagger / documentação das rotas
		http://127.0.0.1:9000/health → health check
		http://127.0.0.1:9000/admin → painel admin
		http://127.0.0.1:9000/client/FLX-001 → dashboard do cliente
		http://127.0.0.1:9000/client/FLX-001/campaigns → campanhas do cliente
		http://127.0.0.1:9000/totem/sim/FLX-001 → simulador visual do totem
		http://127.0.0.1:9000/totem/live/FLX-001 → monitor ao vivo

Gerar relatórios em CMD:
Relatório resumido
		
		sed -n '1,200p' data/metrics/metrics_report.md

Últimas interações de uma empresa

		grep -n '"company_id": "FLX-001"' data/metrics/metrics.jsonl | tail -n 20

Ver campanhas salvas
		
		cat data/campaigns.json

Ver empresas salvas

		cat data/companies.json
	
