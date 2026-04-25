#!/usr/bin/env python3
"""
apply_rds_patch.py
==================
Aplica o patch de integração RDS no arquivo app/routes/totem.py
Execute: python3 apply_rds_patch.py
"""
import re
from pathlib import Path

TARGET = Path("app/routes/totem.py")

if not TARGET.exists():
    print(f"❌  Arquivo não encontrado: {TARGET}")
    exit(1)

original = TARGET.read_text()
backup = TARGET.with_suffix(".py.bak")
backup.write_text(original)
print(f"✅  Backup salvo em {backup}")

# ── 1. Adicionar imports ──────────────────────────────────────────────────────
OLD_IMPORTS = "from core.totem.session_store import get_or_create_session, increment_turn"
NEW_IMPORTS = """from core.totem.session_store import get_or_create_session, increment_turn

# ── AWS RDS (importação segura — não derruba se não configurado) ──
try:
    import asyncio as _asyncio
    from app.services.aws_db_service import db as _rds
    _RDS_OK = True
except Exception:
    _RDS_OK = False
    _rds = None

def _save_rds(coro):
    \"\"\"Dispara uma coroutine no event loop sem bloquear o endpoint.\"\"\"
    if not _RDS_OK:
        return
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except Exception as exc:
        logger.warning("RDS save error: %s", exc)"""

patched = original.replace(OLD_IMPORTS, NEW_IMPORTS)
if OLD_IMPORTS not in original:
    print("❌  Import âncora não encontrado — verifique se o arquivo não mudou.")
    exit(1)

# ── 2. Patch em totem_activate ─────────────────────────────────────────────────
OLD_ACTIVATE_RETURN = """    return TotemActivateResponse(
        session_id=st["session_id"] if isinstance(st, dict) else st.session_id,
        language="pt",
        greeting=greeting,
        next="listening",
        audio_base64=audio_base64,
        audio_provider=audio_provider,
        audio_error=audio_error,
    )"""

NEW_ACTIVATE_RETURN = """    # ── Salva sessão no RDS ──────────────────────────────────────────────────
    _session_id = st["session_id"] if isinstance(st, dict) else st.session_id
    _save_rds(_rds.save_session_start(
        session_id=_session_id,
        company_id=req.company_id,
        device_id=getattr(req, "device_id", None),
    ))

    return TotemActivateResponse(
        session_id=_session_id,
        language="pt",
        greeting=greeting,
        next="listening",
        audio_base64=audio_base64,
        audio_provider=audio_provider,
        audio_error=audio_error,
    )"""

if OLD_ACTIVATE_RETURN not in patched:
    print("❌  Bloco return de totem_activate não encontrado.")
    exit(1)
patched = patched.replace(OLD_ACTIVATE_RETURN, NEW_ACTIVATE_RETURN)
print("✅  Patch em totem_activate aplicado")

# ── 3. Patch em totem_interact ─────────────────────────────────────────────────
OLD_INTERACT_RETURN = """    audio_base64 = audio_file_to_base64(audio_path)

    return TotemInteractResponse(
        session_id=req.session_id,
        language=idioma,
        text=text,
        recommendations=recs,
        audio_base64=audio_base64,
        audio_provider=metric.get("tts_provider"),
        response_source=metric.get("response_source") or metric.get("source"),
        metrics=metric,
    )"""

NEW_INTERACT_RETURN = """    audio_base64 = audio_file_to_base64(audio_path)

    # ── Salva interação no RDS ────────────────────────────────────────────────
    _save_rds(_rds.save_interaction(
        session_id=req.session_id,
        company_id=req.company_id,
        message_user=pergunta,
        message_bot=text,
        input_mode=("audio" if req.audio_base64 else (req.input_mode or "text")),
        response_source=metric.get("response_source") or metric.get("source"),
        response_time_ms=int(metric.get("response_time_ms") or 0) or None,
        turn_number=turn,
    ))

    return TotemInteractResponse(
        session_id=req.session_id,
        language=idioma,
        text=text,
        recommendations=recs,
        audio_base64=audio_base64,
        audio_provider=metric.get("tts_provider"),
        response_source=metric.get("response_source") or metric.get("source"),
        metrics=metric,
    )"""

if OLD_INTERACT_RETURN not in patched:
    print("❌  Bloco return de totem_interact não encontrado.")
    exit(1)
patched = patched.replace(OLD_INTERACT_RETURN, NEW_INTERACT_RETURN)
print("✅  Patch em totem_interact aplicado")

# ── 4. Patch em totem_nps ──────────────────────────────────────────────────────
OLD_NPS_RETURN = """    return TotemNPSResponse(ok=True, message="Obrigado pela avaliação!")"""

NEW_NPS_RETURN = """    # ── Salva NPS no RDS ─────────────────────────────────────────────────────
    _save_rds(_rds.save_nps(
        company_id=req.company_id,
        score=req.score,
        session_id=req.session_id,
        comment=req.comment,
    ))
    # ── Encerra sessão no RDS ─────────────────────────────────────────────────
    _save_rds(_rds.save_session_end(
        session_id=req.session_id,
        end_reason="nps_done",
    ))

    return TotemNPSResponse(ok=True, message="Obrigado pela avaliação!")"""

if OLD_NPS_RETURN not in patched:
    print("❌  Bloco return de totem_nps não encontrado.")
    exit(1)
patched = patched.replace(OLD_NPS_RETURN, NEW_NPS_RETURN)
print("✅  Patch em totem_nps aplicado")

# ── Salva o arquivo ────────────────────────────────────────────────────────────
TARGET.write_text(patched)
print(f"\n🎉  {TARGET} atualizado com sucesso!")
print("   Reinicie o servidor: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
