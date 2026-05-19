from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg

logger = logging.getLogger("aws_db")

_pool: asyncpg.Pool | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _rds_enabled() -> bool:
    required = [
        "AWS_DB_HOST",
        "AWS_DB_NAME",
        "AWS_DB_USER",
        "AWS_DB_PASSWORD",
    ]
    return all(_env(name) for name in required)


def _build_dsn() -> str:
    return (
        f"postgresql://{_env('AWS_DB_USER')}:{_env('AWS_DB_PASSWORD')}"
        f"@{_env('AWS_DB_HOST')}:{_env('AWS_DB_PORT', '5432')}/{_env('AWS_DB_NAME')}"
    )


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


async def init_db_pool() -> None:
    global _pool

    if _pool:
        return

    if not _rds_enabled():
        logger.warning("RDS desativado: variáveis AWS_DB_* incompletas.")
        return

    timeout = float(_env("AWS_DB_CONNECT_TIMEOUT_SECONDS", "3"))

    try:
        _pool = await asyncio.wait_for(
            asyncpg.create_pool(
                dsn=_build_dsn(),
                min_size=1,
                max_size=5,
                command_timeout=5,
                ssl="require",
            ),
            timeout=timeout,
        )
        logger.info("RDS conectado.")
    except Exception as exc:
        logger.warning("RDS indisponível no startup; seguindo sem RDS: %s", type(exc).__name__)
        _pool = None


async def close_db_pool() -> None:
    global _pool

    if _pool:
        await _pool.close()
    _pool = None


class AWSDBService:
    async def save_session_start(
        self,
        session_id: str,
        company_id: str,
        device_id: str | None = None,
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, company_id, device_id, started_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (session_id) DO NOTHING
                """,
                session_id,
                company_id,
                device_id,
                _now(),
            )

    async def save_session_end(
        self,
        session_id: str,
        reason: str = "completed",
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sessions
                SET ended_at = $2,
                    total_turns = (
                        SELECT COUNT(*)
                        FROM interactions
                        WHERE interactions.session_id = sessions.session_id
                    )
                WHERE session_id = $1
                """,
                session_id,
                _now(),
            )

    async def save_interaction(
        self,
        session_id: str,
        company_id: str,
        message_user: str,
        message_bot: str,
        response_source: str | None = None,
        response_time_ms: int | None = None,
        language_detected: str | None = None,
        llm_meta: dict[str, Any] | None = None,
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            turn_index = await conn.fetchval(
                """
                SELECT COALESCE(MAX(turn_index), 0) + 1
                FROM interactions
                WHERE session_id = $1
                """,
                session_id,
            )

            latency_total_s = round((response_time_ms or 0) / 1000, 3)

            await conn.execute(
                """
                INSERT INTO interactions (
                    session_id,
                    company_id,
                    turn_index,
                    input_mode,
                    question,
                    response,
                    language_detected,
                    llm_provider_used,
                    latency_llm_s,
                    latency_tts_s,
                    latency_total_s,
                    llm_meta,
                    created_at
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13)
                """,
                session_id,
                company_id,
                turn_index,
                "text",
                message_user,
                message_bot,
                language_detected,
                response_source,
                latency_total_s,
                None,
                latency_total_s,
                _json(llm_meta),
                _now(),
            )

            await conn.execute(
                """
                UPDATE sessions
                SET total_turns = COALESCE(total_turns, 0) + 1
                WHERE session_id = $1
                """,
                session_id,
            )

    async def save_event(
        self,
        company_id: str,
        event_type: str,
        session_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO events (company_id, session_id, event_type, payload, created_at)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                """,
                company_id,
                session_id,
                event_type,
                _json(payload),
                _now(),
            )

    async def save_nps(
        self,
        company_id: str,
        session_id: str,
        score: int,
        comment: str | None = None,
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO nps (company_id, session_id, score, comment, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                company_id,
                session_id,
                score,
                comment,
                _now(),
            )

    async def save_conversion(
        self,
        company_id: str,
        session_id: str,
        campaign_id: str | None = None,
        action_id: str | None = None,
        action_label: str | None = None,
        value: float = 0,
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversions (
                    company_id,
                    session_id,
                    campaign_id,
                    action_id,
                    action_label,
                    value,
                    created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                company_id,
                session_id,
                campaign_id,
                action_id,
                action_label,
                value,
                _now(),
            )

    async def insert_metric(self, payload: dict[str, Any]) -> None:
        if not _pool:
            raise RuntimeError("RDS pool indisponível.")

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO metrics_events (
                    company_id,
                    session_id,
                    event_type,
                    payload,
                    created_at
                )
                VALUES ($1, $2, $3, $4::jsonb, COALESCE($5, NOW()))
                """,
                payload.get("company_id"),
                payload.get("session_id"),
                payload.get("event") or payload.get("event_type") or "unknown",
                _json(payload),
                _parse_dt(payload.get("timestamp") or payload.get("created_at")),
            )

    async def upsert_lead(self, payload: dict[str, Any]) -> None:
        if not _pool:
            raise RuntimeError("RDS pool indisponível.")

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO leads (
                    lead_id,
                    company_id,
                    session_id,
                    full_name,
                    email,
                    cpf,
                    phone,
                    age,
                    gender,
                    favorite_brands,
                    lgpd_consent,
                    newsletter_opt_in,
                    consent_version,
                    source,
                    ip_address,
                    user_agent,
                    access_page_url,
                    recovery_page_url,
                    access_qr_url,
                    recovery_qr_url,
                    payload,
                    created_at,
                    updated_at
                )
                VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,
                    $11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
                    $21::jsonb,
                    COALESCE($22, NOW()),
                    COALESCE($23, NOW())
                )
                ON CONFLICT (lead_id)
                DO UPDATE SET
                    company_id = EXCLUDED.company_id,
                    session_id = EXCLUDED.session_id,
                    full_name = EXCLUDED.full_name,
                    email = EXCLUDED.email,
                    cpf = EXCLUDED.cpf,
                    phone = EXCLUDED.phone,
                    age = EXCLUDED.age,
                    gender = EXCLUDED.gender,
                    favorite_brands = EXCLUDED.favorite_brands,
                    lgpd_consent = EXCLUDED.lgpd_consent,
                    newsletter_opt_in = EXCLUDED.newsletter_opt_in,
                    consent_version = EXCLUDED.consent_version,
                    source = EXCLUDED.source,
                    ip_address = EXCLUDED.ip_address,
                    user_agent = EXCLUDED.user_agent,
                    access_page_url = EXCLUDED.access_page_url,
                    recovery_page_url = EXCLUDED.recovery_page_url,
                    access_qr_url = EXCLUDED.access_qr_url,
                    recovery_qr_url = EXCLUDED.recovery_qr_url,
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                """,
                payload["lead_id"],
                payload["company_id"],
                payload["session_id"],
                payload.get("full_name"),
                payload["email"],
                payload.get("cpf"),
                payload.get("phone"),
                int(payload.get("age") or 0),
                payload.get("gender"),
                _json(payload.get("favorite_brands") or []),
                bool(payload.get("lgpd_consent")),
                bool(payload.get("newsletter_opt_in", True)),
                payload.get("consent_version"),
                payload.get("source"),
                payload.get("ip_address"),
                payload.get("user_agent"),
                payload.get("access_page_url"),
                payload.get("recovery_page_url"),
                payload.get("access_qr_url"),
                payload.get("recovery_qr_url"),
                _json(payload),
                _parse_dt(payload.get("created_at") or payload.get("timestamp")),
                _parse_dt(payload.get("updated_at")),
            )

    async def insert_consent(self, payload: dict[str, Any]) -> None:
        if not _pool:
            raise RuntimeError("RDS pool indisponível.")

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO consents (
                    consent_id,
                    company_id,
                    session_id,
                    lead_id,
                    email,
                    full_name,
                    lgpd_consent,
                    newsletter_opt_in,
                    consent_version,
                    consent_text,
                    source,
                    ip_address,
                    user_agent,
                    payload,
                    created_at
                )
                VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                    $14::jsonb,
                    COALESCE($15, NOW())
                )
                ON CONFLICT (consent_id) DO NOTHING
                """,
                payload["consent_id"],
                payload["company_id"],
                payload["session_id"],
                payload.get("lead_id"),
                payload["email"],
                payload.get("full_name"),
                bool(payload.get("lgpd_consent")),
                bool(payload.get("newsletter_opt_in", True)),
                payload.get("consent_version"),
                payload.get("consent_text"),
                payload.get("source"),
                payload.get("ip_address"),
                payload.get("user_agent"),
                _json(payload),
                _parse_dt(payload.get("timestamp") or payload.get("created_at")),
            )

    async def record_sync_audit(self, sync_item: dict[str, Any], status: str, error: str | None = None) -> None:
        if not _pool:
            raise RuntimeError("RDS pool indisponível.")

        async with _pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sync_audit (
                    sync_id,
                    entity,
                    operation,
                    company_id,
                    session_id,
                    status,
                    attempts,
                    last_error,
                    payload,
                    created_at,
                    synced_at
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,COALESCE($10, NOW()),$11)
                ON CONFLICT (sync_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    attempts = EXCLUDED.attempts,
                    last_error = EXCLUDED.last_error,
                    payload = EXCLUDED.payload,
                    synced_at = EXCLUDED.synced_at
                """,
                sync_item["sync_id"],
                sync_item.get("entity"),
                sync_item.get("operation"),
                sync_item.get("company_id"),
                sync_item.get("session_id"),
                status,
                int(sync_item.get("attempts") or 0),
                error,
                _json(sync_item.get("payload") or {}),
                _parse_dt(sync_item.get("timestamp")),
                _now() if status == "synced" else None,
            )
