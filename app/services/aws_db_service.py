"""
app/services/aws_db_service.py
==============================
Serviço assíncrono de persistência no RDS PostgreSQL (AWS).
Funciona como camada paralela ao JSONL local — se o RDS estiver
indisponível, loga o erro e continua sem derrubar o totem.

Uso nos seus endpoints existentes:
    from app.services.aws_db_service import db

    await db.save_session_start(session_id, company_id, device_id)
    await db.save_interaction(...)
    await db.save_nps(...)
"""

from __future__ import annotations

import hashlib
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncpg

logger = logging.getLogger("aws_db")

# ─── Pool global ────────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None


async def init_db_pool() -> None:
    """Inicializa o pool de conexões.  Chamar em startup do FastAPI."""
    global _pool
    dsn = _build_dsn()
    if not dsn:
        logger.warning("AWS_DB_* não configurado — RDS desativado.")
        return
    try:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=10,
            ssl="require",           # RDS exige TLS
        )
        logger.info("✅  Pool RDS conectado: %s", os.getenv("AWS_DB_HOST"))
    except Exception as exc:
        logger.error("❌  Falha ao conectar RDS: %s", exc)
        _pool = None


async def close_db_pool() -> None:
    """Fecha o pool.  Chamar em shutdown do FastAPI."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def _build_dsn() -> str | None:
    host = os.getenv("AWS_DB_HOST")
    if not host:
        return None
    return (
        f"postgresql://{os.getenv('AWS_DB_USER', 'postgres')}:"
        f"{os.getenv('AWS_DB_PASSWORD')}@"
        f"{host}:{os.getenv('AWS_DB_PORT', '5432')}/"
        f"{os.getenv('AWS_DB_NAME', 'iagora')}"
    )


@asynccontextmanager
async def _conn():
    """Contexto que fornece uma conexão ou faz no-op se o pool for None."""
    if _pool is None:
        yield None
        return
    async with _pool.acquire() as conn:
        yield conn


# ─── Helper interno ──────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_cpf(cpf: str | None) -> str | None:
    if not cpf:
        return None
    digits = "".join(c for c in cpf if c.isdigit())
    return hashlib.sha256(digits.encode()).hexdigest()


async def _exec(sql: str, *args: Any) -> None:
    """Executa uma query ignorando erros para não derrubar o totem."""
    async with _conn() as conn:
        if conn is None:
            return
        try:
            await conn.execute(sql, *args)
        except Exception as exc:
            logger.error("RDS exec error — %s | args=%s | %s", sql[:80], args, exc)


# ─── API pública ─────────────────────────────────────────────────────────────


class AWSDBService:
    """Fachada de alto nível para o restante da aplicação."""

    # ── Sessões ───────────────────────────────────────────────────────────────

    async def save_session_start(
        self,
        session_id: str,
        company_id: str,
        device_id: str | None = None,
    ) -> None:
        await _exec(
            """
            INSERT INTO sessions (session_id, company_id, device_id, started_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (session_id) DO NOTHING
            """,
            session_id, company_id, device_id, _now(),
        )

    async def save_session_end(
        self,
        session_id: str,
        end_reason: str = "completed",
        interaction_count: int = 0,
    ) -> None:
        ended = _now()
        await _exec(
            """
            UPDATE sessions
            SET ended_at          = $2,
                end_reason        = $3,
                interaction_count = $4,
                duration_s        = EXTRACT(EPOCH FROM ($2 - started_at))::INTEGER
            WHERE session_id = $1
            """,
            session_id, ended, end_reason, interaction_count,
        )

    # ── Interações ────────────────────────────────────────────────────────────

    async def save_interaction(
        self,
        session_id: str,
        company_id: str,
        message_user: str,
        message_bot: str,
        input_mode: str = "text",
        response_source: str | None = None,
        response_time_ms: int | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        turn_number: int = 1,
    ) -> None:
        await _exec(
            """
            INSERT INTO interactions
                (session_id, company_id, turn_number, input_mode,
                 message_user, message_bot, response_source,
                 response_time_ms, tokens_input, tokens_output, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
            session_id, company_id, turn_number, input_mode,
            message_user, message_bot, response_source,
            response_time_ms, tokens_input, tokens_output, _now(),
        )

    # ── Presença ──────────────────────────────────────────────────────────────

    async def save_presence_event(
        self,
        company_id: str,
        device_id: str,
        event_type: str,
        session_id: str | None = None,
        image_s3_key: str | None = None,
        raw_detections: dict | None = None,
    ) -> None:
        import json
        raw_json = json.dumps(raw_detections) if raw_detections else None
        await _exec(
            """
            INSERT INTO presence_events
                (company_id, device_id, session_id, event_type,
                 image_s3_key, raw_detections, created_at)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7)
            """,
            company_id, device_id, session_id, event_type,
            image_s3_key, raw_json, _now(),
        )

    # ── Leads ─────────────────────────────────────────────────────────────────

    async def save_lead(
        self,
        lead_id: str,
        company_id: str,
        session_id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        cpf: str | None = None,
        phone: str | None = None,
        age: int | None = None,
        gender: str | None = None,
        lgpd_accepted: bool = False,
        research_summary: str | None = None,
    ) -> None:
        await _exec(
            """
            INSERT INTO leads
                (lead_id, session_id, company_id, name, email, cpf_hash,
                 phone, age, gender, lgpd_accepted, lgpd_accepted_at,
                 research_summary, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            ON CONFLICT (lead_id) DO UPDATE SET
                name             = EXCLUDED.name,
                email            = EXCLUDED.email,
                phone            = EXCLUDED.phone,
                age              = EXCLUDED.age,
                gender           = EXCLUDED.gender,
                lgpd_accepted    = EXCLUDED.lgpd_accepted,
                lgpd_accepted_at = EXCLUDED.lgpd_accepted_at,
                research_summary = EXCLUDED.research_summary
            """,
            lead_id, session_id, company_id, name, email, _hash_cpf(cpf),
            phone, age, gender, lgpd_accepted,
            _now() if lgpd_accepted else None,
            research_summary, _now(),
        )

    # ── Cupons ────────────────────────────────────────────────────────────────

    async def save_coupon(
        self,
        coupon_id: str,
        company_id: str,
        lead_id: str | None = None,
        campaign_id: str | None = None,
        discount_pct: float = 0,
        expires_at: datetime | None = None,
        qr_url: str | None = None,
    ) -> None:
        await _exec(
            """
            INSERT INTO coupons
                (coupon_id, lead_id, campaign_id, company_id,
                 discount_pct, status, issued_at, expires_at, qr_url)
            VALUES ($1,$2,$3,$4,$5,'active',$6,$7,$8)
            ON CONFLICT (coupon_id) DO NOTHING
            """,
            coupon_id, lead_id, campaign_id, company_id,
            discount_pct, _now(), expires_at, qr_url,
        )

    async def redeem_coupon(
        self,
        coupon_id: str,
        store_id: str | None = None,
        operator_id: str | None = None,
    ) -> None:
        await _exec(
            """
            UPDATE coupons
            SET status      = 'redeemed',
                redeemed_at = $2,
                store_id    = $3,
                operator_id = $4
            WHERE coupon_id = $1 AND status = 'active'
            """,
            coupon_id, _now(), store_id, operator_id,
        )

    # ── NPS ───────────────────────────────────────────────────────────────────

    async def save_nps(
        self,
        company_id: str,
        score: int,
        session_id: str | None = None,
        comment: str | None = None,
    ) -> None:
        await _exec(
            """
            INSERT INTO nps_scores
                (session_id, company_id, score, comment, created_at)
            VALUES ($1,$2,$3,$4,$5)
            """,
            session_id, company_id, score, comment, _now(),
        )

    # ── Visão computacional (ML futuro) ───────────────────────────────────────

    async def save_vision_detection(
        self,
        company_id: str,
        session_id: str | None = None,
        presence_event_id: int | None = None,
        model_name: str = "deepface",
        model_version: str | None = None,
        detected_gender: str | None = None,
        gender_confidence: float | None = None,
        detected_age: int | None = None,
        emotion: str | None = None,
        raw_output: dict | None = None,
        image_s3_key: str | None = None,
    ) -> None:
        import json

        age_range = _age_to_range(detected_age)
        raw_json = json.dumps(raw_output) if raw_output else None

        await _exec(
            """
            INSERT INTO vision_detections
                (session_id, company_id, presence_event_id,
                 model_name, model_version,
                 detected_gender, gender_confidence,
                 detected_age, detected_age_range,
                 emotion, raw_output, image_s3_key, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12,$13)
            """,
            session_id, company_id, presence_event_id,
            model_name, model_version,
            detected_gender, gender_confidence,
            detected_age, age_range,
            emotion, raw_json, image_s3_key, _now(),
        )

        # Atualiza a sessão com o dado de visão
        if session_id and (detected_gender or detected_age):
            await _exec(
                """
                UPDATE sessions SET
                    detected_gender    = COALESCE($2, detected_gender),
                    detected_age_range = COALESCE($3, detected_age_range),
                    vision_confidence  = COALESCE($4, vision_confidence)
                WHERE session_id = $1
                """,
                session_id, detected_gender, age_range, gender_confidence,
            )

    # ── Campanhas ─────────────────────────────────────────────────────────────

    async def save_campaign(
        self,
        campaign_id: str,
        company_id: str,
        title: str,
        description: str | None = None,
        discount_pct: float = 0,
        media_url: str | None = None,
        target_gender: str | None = None,
        target_age_min: int | None = None,
        target_age_max: int | None = None,
        active: bool = True,
    ) -> None:
        await _exec(
            """
            INSERT INTO campaigns
                (campaign_id, company_id, title, description,
                 discount_pct, media_url,
                 target_gender, target_age_min, target_age_max,
                 active, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (campaign_id) DO UPDATE SET
                title          = EXCLUDED.title,
                description    = EXCLUDED.description,
                discount_pct   = EXCLUDED.discount_pct,
                media_url      = EXCLUDED.media_url,
                target_gender  = EXCLUDED.target_gender,
                target_age_min = EXCLUDED.target_age_min,
                target_age_max = EXCLUDED.target_age_max,
                active         = EXCLUDED.active
            """,
            campaign_id, company_id, title, description,
            discount_pct, media_url,
            target_gender, target_age_min, target_age_max,
            active, _now(),
        )

    # ── Consultas para dashboard ───────────────────────────────────────────────

    async def get_daily_metrics(
        self, company_id: str, days: int = 30
    ) -> list[dict]:
        async with _conn() as conn:
            if conn is None:
                return []
            try:
                rows = await conn.fetch(
                    """
                    SELECT * FROM daily_metrics
                    WHERE company_id = $1
                      AND day >= NOW() - ($2 || ' days')::INTERVAL
                    ORDER BY day DESC
                    """,
                    company_id, str(days),
                )
                return [dict(r) for r in rows]
            except Exception as exc:
                logger.error("get_daily_metrics: %s", exc)
                return []

    async def get_recent_sessions(
        self, company_id: str, limit: int = 20
    ) -> list[dict]:
        async with _conn() as conn:
            if conn is None:
                return []
            try:
                rows = await conn.fetch(
                    """
                    SELECT s.session_id, s.started_at, s.ended_at,
                           s.duration_s, s.interaction_count,
                           s.detected_gender, s.detected_age_range,
                           n.score AS nps_score
                    FROM sessions s
                    LEFT JOIN nps_scores n ON n.session_id = s.session_id
                    WHERE s.company_id = $1
                    ORDER BY s.started_at DESC
                    LIMIT $2
                    """,
                    company_id, limit,
                )
                return [dict(r) for r in rows]
            except Exception as exc:
                logger.error("get_recent_sessions: %s", exc)
                return []


# ─── Instância global ─────────────────────────────────────────────────────────

db = AWSDBService()


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _age_to_range(age: int | None) -> str | None:
    if age is None:
        return None
    brackets = [(18, "0-17"), (25, "18-24"), (35, "25-34"),
                (45, "35-44"), (55, "45-54"), (65, "55-64")]
    for threshold, label in brackets:
        if age < threshold:
            return label
    return "65+"
