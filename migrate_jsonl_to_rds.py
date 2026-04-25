import asyncio, json, os, hashlib, logging
from pathlib import Path
from datetime import datetime, timezone
import asyncpg
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("migrate")
COMPANY_ID = os.getenv("DEFAULT_COMPANY_ID", "FLX-001")
def _dsn():
    return f"postgresql://{os.getenv('AWS_DB_USER','postgres')}:{os.getenv('AWS_DB_PASSWORD')}@{os.getenv('AWS_DB_HOST')}:{os.getenv('AWS_DB_PORT','5432')}/{os.getenv('AWS_DB_NAME','iagora')}"
def _now(): return datetime.now(timezone.utc)
def _load_jsonl(path):
    p = Path(path)
    if not p.exists(): return []
    records = []
    for line in p.open():
        line = line.strip()
        if line:
            try: records.append(json.loads(line))
            except: pass
    return records
async def main():
    log.info("Conectando ao RDS...")
    conn = await asyncpg.connect(dsn=_dsn(), ssl="require")
    metrics = _load_jsonl("data/metrics/metrics.jsonl")
    s, i = 0, 0
    for r in metrics:
        sid = r.get("session_id")
        cid = r.get("company_id", COMPANY_ID)
        ts = _now()
        event = r.get("event_type","")
        if event == "session_started" and sid:
            try:
                await conn.execute("INSERT INTO sessions (session_id, company_id, started_at) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", sid, cid, ts)
                s += 1
            except: pass
        elif event in ("interaction","user_message") and sid:
            try:
                await conn.execute("INSERT INTO interactions (session_id, company_id, message_user, message_bot, created_at) VALUES ($1,$2,$3,$4,$5)", sid, cid, r.get("message_user"), r.get("message_bot"), ts)
                i += 1
            except: pass
    log.info(f"Sessões: {s} | Interações: {i}")
    nps = _load_jsonl("data/nps/nps.jsonl")
    n = 0
    for r in nps:
        score = r.get("score") or r.get("nps_score")
        if score:
            try:
                await conn.execute("INSERT INTO nps (session_id, company_id, score, created_at) VALUES ($1,$2,$3,$4)", r.get("session_id"), r.get("company_id", COMPANY_ID), int(score), _now())
                n += 1
            except: pass
    log.info(f"NPS: {n}")
    await conn.close()
    log.info("Migração concluída!")
asyncio.run(main())
