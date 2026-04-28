from __future__ import annotations

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


async def init_db_pool() -> None:
    global _pool

    host = os.getenv("AWS_DB_HOST")
    if not host:
        logger.warning("AWS_DB_HOST não configurado; RDS desativado.")
        return

    dsn = (
        f"postgresql://{os.getenv('AWS_DB_USER')}:{os.getenv('AWS_DB_PASSWORD')}"
        f"@{host}:{os.getenv('AWS_DB_PORT', '5432')}/{os.getenv('AWS_DB_NAME')}"
    )

    try:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=10,
            ssl="require",
        )
        logger.info("RDS conectado.")
    except Exception as exc:
        logger.error("Erro RDS: %s", exc)
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
            try:
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
            except Exception as exc:
                logger.error("RDS session start error: %s", exc)

    async def save_session_end(
        self,
        session_id: str,
        reason: str = "completed",
    ) -> None:
        if not _pool:
            return

        async with _pool.acquire() as conn:
            try:
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
            except Exception as exc:
                logger.error("RDS session end error: %s", exc)

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
            try:
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
                    json.dumps(llm_meta or {}, ensure_ascii=False),
                    _now(),
                )
            except Exception as exc:
                logger.error("RDS interaction error: %s", exc)

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
            try:
                await conn.execute(
                    """
                    INSERT INTO events (company_id, session_id, event_type, payload, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    company_id,
                    session_id,
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False),
                    _now(),
                )
            except Exception as exc:
                logger.error("RDS event error: %s", exc)

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
            try:
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
            except Exception as exc:
                logger.error("RDS nps error: %s", exc)

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
            try:
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
            except Exception as exc:
                logger.error("RDS conversion error: %s", exc)
