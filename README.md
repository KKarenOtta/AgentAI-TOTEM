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
	HUGGING_FACE_API_KEY=


APÓS TRABALHAR NAS SUAS ALTERAÇOES: criar o COMMIT:
	
		git add .
	
		git commit -m "Descrição das alterações que você realizou”

antes de fazer o push, é uma boa prática puxar as últimas alterações de branch principal para evitar conflitos: 
		
		git pull request origin main/master
		
		git push -u origin nome-do-branch


Atualizar o Branch Local
Após a mesclagem, cada membro deve atualizar seu branch local para garantir que está trabalhando com a versão mais recente:
		
		git checkout main
		
		git pull origin main


+++ DIA-A-DIA: Antes de iniciar o trabalho diário em seu projeto, é importante garantir que você esteja trabalhando com a versão mais recente do código. Aqui está um passo a passo para atualizar seu projeto e continuar:
Entre na sua pasta de projeto da sua máquina:
	ex: cd "/Users/karenota/Desktop/AgentAI-TOTEM”

Ative seu ambiente virtual: 
		
		source venv/bin/activate  # macOS/Linux
		
		venv\Scripts\activate       # Windows


Atualize sua branch principal:
		
		git checkout main

Puxe as últimas alterações do repositório remoto:
		
		git pull origin main

Verifique se há novas dependencias: 
	Se houver alterações nas dependencias do projeto (ex: requirements.txt): 	
		
		pip install -r requirements.txt
		pip install -r requirements-pi.txt

Verifique o status do repositório:
	
		git status

Se houver alterações não comitadas, você pode querer fazer um commit ou stash delas antes de continuar.

Continue seu Trabalho: Agora você pode mudar para o branch onde estava trabalhando ou criar um novo branch para suas alterações:
	  
		git checkout -b nome-do-branch

Para atualizar o requirements utilize:

		pip freeze > requirements.txt
		pip freeze > requirements-pi.txt


Para verificar os templates localmente:
	Certifique-se de estar com o venv ativado!

		python3 -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --log-level debug

Abrir navegador em: 
	- http://127.0.0.1:9000/docs
	- http://127.0.0.1:9000/admin
	- http://127.0.0.1:9000/totem/sim/FLX-001
	- http://127.0.0.1:9000/totem/live/FLX-001
	- http://127.0.0.1:9000/client/demo
	- http://127.0.0.1:9000/client/dashboard

Gerar relatórios em CMD:

		sed -n '1,200p' data/metrics/metrics_report.md
		grep -n '"company_id": "FLX-001"' data/metrics/metrics.jsonl | tail -n 20
	
	
