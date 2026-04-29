<img width="201" height="231" alt="IAgora" src="https://github.com/user-attachments/assets/29dd313b-b9f6-4df1-875f-915245640425" />

# AgentAI-TOTEM — Manual de Execução e Fluxo Completo

## 1. Objetivo

Este documento explica como rodar a aplicação **AgentAI-TOTEM**, quais comandos executar, quais endereços abrir no navegador e como testar o fluxo completo para:

* Usuário final no Totem
* Administrador
* Empresa cadastrada
* Raspberry Pi / sensores
* Backend local
* Fluxo de presença, interação, FAQ, recomendação, cupom e handoff

---

# 2. Visão geral da arquitetura em execução

O projeto funciona com os seguintes blocos principais:

```text
Raspberry Pi / Sensores
        ↓
/api/presence/trigger
        ↓
Backend FastAPI
        ↓
Event Bus / SSE
        ↓
Tela do Totem no navegador
        ↓
Interação do usuário
        ↓
FAQ / Orquestrador / Recomendador / Cupom / Handoff
        ↓
Admin / Empresa acompanham dados e métricas
```

Componentes principais:

| Camada             | Função                                              |
| ------------------ | --------------------------------------------------- |
| Backend FastAPI    | API principal da aplicação                          |
| Totem UI           | Interface usada pelo visitante                      |
| Admin UI           | Gestão, campanhas, dados e métricas                 |
| Empresa cadastrada | Visualização da operação da empresa                 |
| Raspberry Pi       | Captura presença real via sensores/câmera           |
| SSE                | Atualização em tempo real entre backend e Totem     |
| FAQEngine          | Busca semântica de respostas                        |
| Recommender        | Sugestões comerciais e campanhas                    |
| Coupon Store       | Geração e resgate de cupons                         |
| Metrics            | Registro de eventos e conversões                    |
| Handoff            | Link de continuidade da sessão em outro dispositivo |

---

# 3. Pré-requisitos

## 3.1. Ative o ambiente virtual:

```bash
source venv/bin/activate
```

Se o ambiente virtual não existir:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

# 4. Como rodar o backend principal

## 4.1. Rodar em modo desenvolvimento local

Use este comando no Mac:

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir app \
  --reload-dir core \
  --reload-dir edge \
  --reload-dir templates \
  --reload-dir static \
  --reload-dir marketing \
  --reload-dir recommender \
  --reload-dir repositories \
  --reload-dir infra \
  --reload-dir ml
```

Se a porta `8000` estiver ocupada, use a porta `9000`:

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 9000 \
  --reload \
  --reload-dir app \
  --reload-dir core \
  --reload-dir edge \
  --reload-dir templates \
  --reload-dir static \
  --reload-dir marketing \
  --reload-dir recommender \
  --reload-dir repositories \
  --reload-dir infra \
  --reload-dir ml
```

---

# 5. Endereços para abrir no navegador

Assumindo que o backend está rodando na porta `8000`:

## 5.1. Tela do Totem — usuário final

```text
http://127.0.0.1:8000/totem/FLX-001
```

ou:

```text
http://127.0.0.1:8000/totem/live/FLX-001
```

Uso:

* Deve ficar aberta na tela do Totem.
* Aguarda presença real ou simulação.
* Recebe eventos em tempo real via SSE.
* Inicia a experiência do visitante.

---

## 5.2. Dashboard/Admin

```text
http://127.0.0.1:8000/dashboard
```

Uso:

* Visão administrativa geral.
* Acompanhamento de métricas.
* Acesso a recursos internos de operação.

Caso o projeto tenha rotas específicas de analytics, testar também:

```text
http://127.0.0.1:8000/analytics
```

---

## 5.3. Empresa cadastrada

Para a empresa `FLX-001`:

```text
http://127.0.0.1:8000/totem/FLX-001
```

ou, quando houver uma página específica por empresa/dispositivo:

```text
http://127.0.0.1:8000/device/FLX-001
```

Se a sessão gerar um handoff, o link terá formato semelhante a:

```text
http://127.0.0.1:8000/device/FLX-001/<session_id>
```

Exemplo:

```text
http://127.0.0.1:8000/device/FLX-001/totem-ui-1777476761882
```

---

# 6. Fluxo completo — usuário final no Totem

## 6.1. Abrir a tela do Totem

No navegador do computador ou tela do Totem:

```text
http://127.0.0.1:8000/totem/FLX-001
```

Estado esperado inicial:

```text
Aguardando ativação
```

---

## 6.2. Simular presença sem Raspberry Pi

Em outro terminal, execute:

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

curl -X POST "http://127.0.0.1:8000/api/presence/trigger" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "company_id": "FLX-001",
    "device_id": "LOCAL-SENSOR-SIM",
    "present": true
  }'
```

Resposta esperada:

```json
{
  "ok": true,
  "state": {
    "company_id": "FLX-001",
    "device_id": "LOCAL-SENSOR-SIM",
    "present": true
  }
}
```

Na tela do Totem, o estado deve sair de:

```text
Aguardando ativação
```

para uma experiência ativa, saudação ou início de interação.

---

## 6.3. Testar stream de eventos SSE

Em outro terminal:

```bash
curl -N "http://127.0.0.1:8000/api/events/FLX-001"
```

Depois, em outro terminal, dispare presença:

```bash
curl -X POST "http://127.0.0.1:8000/api/presence/trigger" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "company_id": "FLX-001",
    "device_id": "LOCAL-SENSOR-SIM",
    "present": true
  }'
```

Evento esperado no terminal SSE:

```json
{
  "type": "presence_triggered",
  "payload": {
    "company_id": "FLX-001",
    "device_id": "LOCAL-SENSOR-SIM",
    "present": true
  }
}
```

---

## 6.4. Interação do usuário

Depois da ativação, o usuário pode:

1. Receber saudação inicial.
2. Fazer pergunta ao Totem.
3. Receber resposta via FAQ semântico.
4. Receber recomendação baseada em contexto.
5. Receber cupom ou QR Code.
6. Receber link de continuidade da sessão em outro dispositivo.

Exemplo de perguntas:

```text
qual o horário de funcionamento?
```

```text
que horas abre?
```

```text
quero algo bom para criança pequena hoje
```

---

# 7. Fluxo completo — Raspberry Pi / sensores

## 7.1. No Mac, descobrir o IP local

No Mac:

```bash
ipconfig getifaddr en0
```

Exemplo de resultado:

```text
192.168.15.7
```

Este IP deve ser usado pelo Raspberry Pi para chamar o backend.

---

## 7.2. No Raspberry Pi, configurar URL da API

No Raspberry Pi:

```bash
cd ~/AgentAI-TOTEM
source venv/bin/activate
```

A variável `TOTEM_API_URL` deve apontar para o IP do Mac:

```text
http://192.168.15.7:8000/api/presence/trigger
```

Não exponha o conteúdo completo do `.env`. Para verificar apenas nomes e linhas seguras:

```bash
grep -nE "TOTEM_API_URL|COMPANY_ID|DEVICE_ID|PRESENCE|CAMERA" .env .env.example 2>/dev/null
```

---

## 7.3. Rodar sensores no Raspberry Pi

### Runtime com sensores ultrassônicos, DHT e câmera

```bash
cd ~/AgentAI-TOTEM
source venv/bin/activate

python edge/raspberry_runtime/sensor_runtime.py
```

Saída esperada:

```text
Raspberry Runtime iniciado
Sensores: ultrassônicos + DHT + câmera
API: http://192.168.15.7:8000/api/presence/trigger
COMPANY_ID: FLX-001
DEVICE_ID: RPI3-SENSORS-001
```

Quando detectar presença real, deve aparecer algo como:

```text
Presença real detectada
[API] 200 | {"ok":true,...}
```

---

### Runtime antigo com PIR

Se estiver usando o sender baseado em PIR:

```bash
cd ~/AgentAI-TOTEM
source venv/bin/activate

python edge/raspberry_presence_sender/main.py
```

Saída esperada:

```text
Presence sender iniciado
PIR_PIN=17
Aguardando estabilização do PIR por 5s...
Sensor estabilizado. Monitorando presença...
```

---

# 8. Fluxo completo — Admin

## 8.1. Acessar dashboard

No navegador:

```text
http://127.0.0.1:8000/dashboard
```

Funções esperadas:

* Visualizar operação geral.
* Ver empresas/campanhas se implementado na interface.
* Acompanhar métricas.
* Auditar interações.
* Validar cupons e conversões.

---

## 8.2. Verificar métricas salvas

No terminal:

```bash
cd ~/Desktop/AgentAI-TOTEM

ls -lh data/metrics 2>/dev/null
cat data/metrics/metrics.jsonl 2>/dev/null | tail -n 20
```

Eventos esperados:

```json
{"event":"coupon_redeemed", ...}
```

ou eventos de interação, sessão, recomendação e conversão, dependendo do fluxo executado.

---

## 8.3. Verificar leads salvos

```bash
cd ~/Desktop/AgentAI-TOTEM

ls -lh data/leads 2>/dev/null
cat data/leads/leads.jsonl 2>/dev/null | tail -n 20
```

---

## 8.4. Verificar consentimentos LGPD

```bash
cd ~/Desktop/AgentAI-TOTEM

ls -lh data/lgpd 2>/dev/null
cat data/lgpd/consents.jsonl 2>/dev/null | tail -n 20
```

---

## 8.5. Verificar handoffs de sessão

```bash
cd ~/Desktop/AgentAI-TOTEM

ls -lt data/device_handoffs 2>/dev/null | head
LATEST=$(ls -t data/device_handoffs/*.json 2>/dev/null | head -n 1)
echo "$LATEST"
cat "$LATEST"
```

Exemplo esperado:

```json
{
  "company_id": "FLX-001",
  "session_id": "totem-ui-...",
  "summary": "Sessão iniciada no totem.",
  "link": "http://127.0.0.1:8000/device/FLX-001/...",
  "map_url": "https://zoologico.com.br/sobre/mapa-zoo-sao-paulo"
}
```

---

# 9. Fluxo completo — empresa cadastrada

A empresa cadastrada, no cenário atual, usa o `company_id`:

```text
FLX-001
```

## 9.1. Abrir experiência da empresa

```text
http://127.0.0.1:8000/totem/FLX-001
```

ou:

```text
http://127.0.0.1:8000/totem/live/FLX-001
```

---

## 9.2. Verificar eventos da empresa em tempo real

```bash
curl -N "http://127.0.0.1:8000/api/events/FLX-001"
```

---

## 9.3. Testar presença vinculada à empresa

```bash
curl -X POST "http://127.0.0.1:8000/api/presence/trigger" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "company_id": "FLX-001",
    "device_id": "EMPRESA-FLX-001-TESTE",
    "present": true
  }'
```

---

## 9.4. Validar dados gerados pela empresa

```bash
cd ~/Desktop/AgentAI-TOTEM

find data -maxdepth 3 -type f | sort
```

Arquivos relevantes:

```text
data/leads/leads.jsonl
data/lgpd/consents.jsonl
data/metrics/metrics.jsonl
data/recovery/search_memory.jsonl
data/recovery/session_handoffs.jsonl
data/device_handoffs/*.json
```

---

# 10. Teste do FAQ semântico

## 10.1. Rodar teste direto do FAQEngine

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

python - <<'PY'
from ml.semantic.faq_engine import FAQEngine

engine = FAQEngine()

tests = [
    "qual o horário de funcionamento?",
    "que horas abre?",
    "quero algo bom para criança pequena hoje",
]

for query in tests:
    answer, score, matched = engine.search(
        company_id="FLX-001",
        query=query,
        min_score=0.45,
    )

    print("QUERY:", query)
    print("ANSWER:", answer)
    print("SCORE:", score)
    print("MATCHED:", matched)
    print("---")
PY
```

Resultado esperado para horário:

```text
ANSWER: Funcionamos das 9h às 17h.
```

Para pergunta infantil, após cadastro correto de intenção, o ideal é retornar algo semelhante a:

```text
ANSWER: Para crianças pequenas temos atrações em horários especiais e opções de alimentos kids disponíveis na lanchonete.
```

---

# 11. Teste de QR Code / Cupom

## 11.1. Verificar QR Codes gerados

```bash
cd ~/Desktop/AgentAI-TOTEM

find static/uploads/qrcodes -type f 2>/dev/null | sort | tail -n 20
```

---

## 11.2. Verificar eventos de cupom

```bash
cd ~/Desktop/AgentAI-TOTEM

cat data/metrics/metrics.jsonl 2>/dev/null | grep -i "coupon" | tail -n 20
```

---

# 12. Teste de voz / captura

## 12.1. Testar endpoint de captura de voz

```bash
curl -X POST "http://127.0.0.1:8000/api/voice/capture?session_id=debug-voice" -i
```

Resposta esperada:

```json
{"ok":true}
```

Se houver erro no TTS, verificar logs do backend e variáveis de provedor de voz sem expor valores secretos.

Verificação segura:

```bash
grep -nE "TTS|VOICE|ELEVEN|OPENAI" .env .env.example 2>/dev/null
```

---

# 13. Checklist de teste completo local

Use esta sequência para validar o sistema de ponta a ponta.

## Terminal 1 — backend

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir app \
  --reload-dir core \
  --reload-dir edge \
  --reload-dir templates \
  --reload-dir static \
  --reload-dir marketing \
  --reload-dir recommender \
  --reload-dir repositories \
  --reload-dir infra \
  --reload-dir ml
```

---

## Navegador — tela do Totem

```text
http://127.0.0.1:8000/totem/FLX-001
```

---

## Terminal 2 — SSE

```bash
curl -N "http://127.0.0.1:8000/api/events/FLX-001"
```

---

## Terminal 3 — simular presença

```bash
curl -X POST "http://127.0.0.1:8000/api/presence/trigger" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "company_id": "FLX-001",
    "device_id": "LOCAL-SENSOR-SIM",
    "present": true
  }'
```

---

## Terminal 4 — testar FAQ

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

python - <<'PY'
from ml.semantic.faq_engine import FAQEngine

engine = FAQEngine()

for query in [
    "qual o horário de funcionamento?",
    "que horas abre?",
    "quero algo bom para criança pequena hoje",
]:
    answer, score, matched = engine.search(
        company_id="FLX-001",
        query=query,
        min_score=0.45,
    )
    print(query, "=>", answer, score, matched)
PY
```

---

## Terminal 5 — verificar dados salvos

```bash
cd ~/Desktop/AgentAI-TOTEM

echo "==== METRICS ===="
cat data/metrics/metrics.jsonl 2>/dev/null | tail -n 20

echo "==== LEADS ===="
cat data/leads/leads.jsonl 2>/dev/null | tail -n 20

echo "==== CONSENTS ===="
cat data/lgpd/consents.jsonl 2>/dev/null | tail -n 20

echo "==== HANDOFFS ===="
ls -lt data/device_handoffs 2>/dev/null | head
LATEST=$(ls -t data/device_handoffs/*.json 2>/dev/null | head -n 1)
echo "$LATEST"
[ -n "$LATEST" ] && cat "$LATEST"
```

---

# 14. Checklist de teste com Raspberry Pi

## No Mac

Rodar backend:

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Descobrir IP do Mac:

```bash
ipconfig getifaddr en0
```

Abrir Totem:

```text
http://127.0.0.1:8000/totem/FLX-001
```

Abrir SSE:

```bash
curl -N "http://127.0.0.1:8000/api/events/FLX-001"
```

---

## No Raspberry Pi

Rodar runtime:

```bash
cd ~/AgentAI-TOTEM
source venv/bin/activate

python edge/raspberry_runtime/sensor_runtime.py
```

ou:

```bash
cd ~/AgentAI-TOTEM
source venv/bin/activate

python edge/raspberry_presence_sender/main.py
```

Resultado esperado:

1. Raspberry detecta presença.
2. Raspberry envia POST para `/api/presence/trigger`.
3. Backend responde `ok: true`.
4. SSE recebe `presence_triggered`.
5. Tela do Totem ativa a interação.
6. Usuário interage.
7. Sistema salva métricas, sessão, cupom e/ou handoff.

---

# 15. Problemas comuns e diagnóstico

## 15.1. Navegador não abre `127.0.0.1:8000`

Verificar se o backend está rodando:

```bash
curl -i "http://127.0.0.1:8000"
```

Verificar processo usando porta:

```bash
lsof -i :8000
```

Se necessário, usar porta 9000:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

Abrir:

```text
http://127.0.0.1:9000/totem/FLX-001
```

---

## 15.2. Raspberry não consegue acessar o Mac

No Mac, confirme IP:

```bash
ipconfig getifaddr en0
```

No Raspberry, teste conexão:

```bash
curl -i "http://IP_DO_MAC:8000"
```

Exemplo:

```bash
curl -i "http://192.168.15.7:8000"
```

Se falhar:

* Confirmar que Mac e Raspberry estão na mesma rede.
* Confirmar que backend foi iniciado com `--host 0.0.0.0`.
* Confirmar firewall do Mac.
* Confirmar se a porta correta é `8000` ou `9000`.

---

## 15.3. SSE recebe evento, mas tela continua aguardando ativação

Testar SSE diretamente:

```bash
curl -N "http://127.0.0.1:8000/api/events/FLX-001"
```

Disparar presença:

```bash
curl -X POST "http://127.0.0.1:8000/api/presence/trigger" \
  -H "Content-Type: application/json" \
  --data-raw '{"company_id":"FLX-001","device_id":"LOCAL-SENSOR-SIM","present":true}'
```

Se o SSE recebe e a tela não muda, o problema provavelmente está no JavaScript/template da página do Totem, não no backend.

Arquivos que devem ser auditados nesse caso:

```text
app/routes/totem.py
templates/totem*.html
static/js/*
infra/realtime/event_bus.py
app/routes/api.py
```

---

## 15.4. Presença retorna `image_required` ou `human_not_validated`

Verificar toggles seguros:

```bash
grep -nE "PRESENCE_REQUIRE_IMAGE|PRESENCE_REQUIRE_HUMAN_VALIDATION" .env .env.example 2>/dev/null
```

Para teste local sem câmera, o `.env` pode usar:

```text
PRESENCE_REQUIRE_IMAGE=false
PRESENCE_REQUIRE_HUMAN_VALIDATION=false
```

Depois reinicie o backend.

---

## 15.5. FAQ responde assunto errado

Executar teste direto:

```bash
cd ~/Desktop/AgentAI-TOTEM
source venv/bin/activate

python - <<'PY'
from ml.semantic.faq_engine import FAQEngine
engine = FAQEngine()
answer, score, matched = engine.search(
    company_id="FLX-001",
    query="quero algo bom para criança pequena hoje",
    min_score=0.45,
)
print(answer, score, matched)
PY
```

Se retornar horário de funcionamento, falta uma intenção específica para crianças/família no dataset do FAQ e nos embeddings persistentes.

---

# 16. Comando de auditoria rápida do projeto

Use este comando para gerar uma visão segura dos principais arquivos sem expor segredos:

```bash
cd ~/Desktop/AgentAI-TOTEM

printf "\n==== GIT STATUS ====\n"
git status --short

printf "\n==== PYTHON FILES PRINCIPAIS ====\n"
find app core infra marketing recommender repositories ml edge -maxdepth 3 -type f \
  | grep -E "\.py$" \
  | sort

printf "\n==== TEMPLATES ====\n"
find templates -maxdepth 3 -type f 2>/dev/null | sort

printf "\n==== STATIC ====\n"
find static -maxdepth 4 -type f 2>/dev/null | sort | head -n 120

printf "\n==== DATA STRUCTURE ====\n"
find data -maxdepth 3 -type f 2>/dev/null | sort

printf "\n==== SAFE ENV KEYS ONLY ====\n"
grep -nE "^[A-Z0-9_]+=" .env .env.example 2>/dev/null | sed 's/=.*$/=***REDACTED***/'
```

---

# 17. Fluxo final esperado em produção/laboratório

## Usuário final

1. Usuário se aproxima do Totem.
2. Sensor detecta presença.
3. Backend valida presença.
4. Tela do Totem ativa saudação.
5. Usuário pergunta algo.
6. FAQEngine responde ou orquestrador direciona.
7. Sistema recomenda campanha/atração/produto.
8. Cupom ou QR Code pode ser gerado.
9. Sessão pode ser continuada no celular via handoff.
10. Eventos são registrados para análise.

---

## Admin

1. Abre dashboard.
2. Acompanha métricas.
3. Audita sessões, leads, consentimentos e cupons.
4. Verifica conversões.
5. Ajusta campanhas e regras.
6. Usa logs e dados para melhorar o modelo.

---

## Empresa cadastrada

1. Possui `company_id`, como `FLX-001`.
2. Tem experiência própria no Totem.
3. Recebe eventos vinculados ao próprio `company_id`.
4. Gera leads, métricas, cupons e handoffs próprios.
5. Pode acompanhar resultados por dashboard, arquivos ou banco de dados.

---

# 18. Resumo dos principais endereços

| Área           | URL                                                                   |
| -------------- | --------------------------------------------------------------------- |
| Totem usuário  | `http://127.0.0.1:8000/totem/FLX-001`                                 |
| Totem live     | `http://127.0.0.1:8000/totem/live/FLX-001`                            |
| Eventos SSE    | `http://127.0.0.1:8000/api/events/FLX-001`                            |
| Dashboard      | `http://127.0.0.1:8000/dashboard`                                     |
| Analytics      | `http://127.0.0.1:8000/analytics`                                     |
| Handoff device | `http://127.0.0.1:8000/device/FLX-001/<session_id>`                   |
| Presença API   | `POST http://127.0.0.1:8000/api/presence/trigger`                     |
| Voz API        | `POST http://127.0.0.1:8000/api/voice/capture?session_id=debug-voice` |

---

# 19. Ordem recomendada para demonstração

1. Abrir backend no Terminal 1.
2. Abrir tela do Totem no navegador.
3. Abrir SSE no Terminal 2.
4. Simular presença no Terminal 3.
5. Confirmar mudança visual no Totem.
6. Fazer pergunta no Totem.
7. Confirmar resposta do FAQ/recomendação.
8. Gerar ou validar cupom/QR.
9. Verificar arquivos salvos em `data/`.
10. Abrir dashboard/admin.
11. Validar fluxo da empresa `FLX-001`.
12. Repetir usando Raspberry Pi real.

---

# 20. Observação importante sobre segurança

Nunca imprimir nem enviar valores reais de:

```text
.env
OPENAI_API_KEY
ELEVENLABS_API_KEY
AWS credentials
DB password
tokens
client secrets
```

Para auditoria, usar somente nomes de variáveis com valores mascarados.

---

# 21. Conclusão

A aplicação deve ser testada em três camadas:

1. **Backend local funcionando** — FastAPI ativo em `8000` ou `9000`.
2. **Fluxo visual do Totem funcionando** — tela muda ao receber presença.
3. **Fluxo operacional completo funcionando** — FAQ, recomendação, cupom, handoff, métricas e dashboard.



TESTE MÍNIMO OBRIGATÓRIO:
Backend ligado → Totem aberto → SSE aberto → presença disparada → tela ativa → interação registrada → dados salvos
	
