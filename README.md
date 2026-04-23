<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

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

Guia de Teste da Aplicação AgentAI-TOTEM
Fluxo operacional, URLs de teste e checklist funcional

Objetivo
	
	Este documento serve para testar a aplicação de ponta a ponta: totem, cadastro mobile, cupons, validação na loja, dashboard e NPS.
	
Pré-requisitos

- Servidor FastAPI ativo em http://127.0.0.1:8000 ou http://192.168.15.6:8000.
- Projeto com .env carregado e diretórios app/, services/ e templates/ monitorados no uvicorn.
- Dispositivo móvel na mesma rede local para testar o handoff via QR.

Endereços para abrir no navegador: 

		http://127.0.0.1:8000/health	Saúde da aplicação	Retorno JSON com status ok.
		http://127.0.0.1:8000/totem/live/FLX-001	Tela principal do totem	Ativação, pergunta, resposta, resumo, recomendações, handoff mobile e NPS.
		http://127.0.0.1:8000/client/FLX-001	Dashboard da empresa	KPIs de leads, cupons, conversão e lojas.
		http://127.0.0.1:8000/client/FLX-001/campaigns	Gestão de campanhas	Campanhas ativas, mídia, cupom e desconto.
		http://127.0.0.1:8000/store/redeem	Validação na loja	Consulta e resgate do cupom com store_id e operator_id.
		http://192.168.15.6:8000/mobile/start/<session_id>	Início do fluxo mobile	Entrada vinda do QR do totem.
		http://192.168.15.6:8000/mobile/capture/<session_id>	Cadastro mobile	Nome, idade, gênero, e-mail, CPF obrigatório e LGPD.
		http://192.168.15.6:8000/mobile/content/<lead_id>	Conteúdo pós-cadastro	Resumo da pesquisa, QR de campanha, cupom e expiração.


Fluxo completo recomendado
	1. Abrir /totem/live/FLX-001.
	2. Simular presença ou ativar atendimento.
	3. Fazer uma pergunta sobre o negócio, por exemplo: "onde fica o banheiro e quais promoções estão ativas?".
	4. Confirmar resposta textual, resumo da pesquisa e ofertas recomendadas.
	5. Clicar em "Continuar no celular" e ler o QR gerado.
	6. No celular, abrir /mobile/start/<session_id>.
	7. Prosseguir para /mobile/capture/<session_id> e preencher o cadastro completo.
	8. Confirmar redirecionamento para /mobile/content/<lead_id>.
	9. Verificar cupom emitido, QR do cupom, expiração e descrição da campanha.
	10. Abrir /store/redeem no dispositivo da loja e validar o coupon_id.
	11. Confirmar status redeemed em data/coupons/coupons.jsonl e métrica coupon_redeemed em data/metrics/metrics.jsonl.
	12. Encerrar o atendimento no totem e registrar uma nota NPS.

Checklist funcional
Resposta local do negócio antes de fallback para IA.
Resumo da pesquisa gerado no totem.
QR de handoff mobile funcional.
CPF obrigatório no cadastro mobile.
Cupom emitido com expires_at, qr_url, store_id e operator_id.
Resgate de cupom altera status para redeemed.
Métrica coupon_redeemed gravada.
Nota NPS gravada ao final.
Teste rápido por terminal

Comandos essenciais:
		
		curl http://127.0.0.1:8000/health
		curl -X POST http://127.0.0.1:8000/totem/activate -H "Content-Type: application/json" -d '{"company_id":"FLX-001","session_id":"fluxo-completo-001"}'
		curl -X POST http://127.0.0.1:8000/totem/interact -H "Content-Type: application/json" -d '{"company_id":"FLX-001","session_id":"fluxo-completo-001","message":"onde fica o banheiro e quais promoções estão ativas?","prefer_audio":false,"input_mode":"text"}'
		curl -X POST http://127.0.0.1:8000/api/mobile-handoff -H "Content-Type: application/json" -d '{"company_id":"FLX-001","session_id":"fluxo-completo-001","research_summary":"Pergunta sobre banheiro e promoções","recommendations_snapshot":{},"source":"totem_live"}'

Observações de teste
Se houver divergência entre o que o totem mostra e o que o terminal retorna, priorize os arquivos JSON e os logs do backend para confirmar o estado real do fluxo.
	
