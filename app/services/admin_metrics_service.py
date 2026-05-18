from __future__ import annotations

from typing import Any

from app.services.aws_db_service import _pool


class AdminMetricsService:
    async def get_overview(
        self,
        company_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        if not _pool:
            return {
                "summary": {
                    "total_sessions": 0,
                    "total_interactions": 0,
                    "total_text": 0,
                    "total_audio": 0,
                },
                "latest_interactions": [],
            }

        safe_limit = max(1, min(int(limit or 10), 100))

        where_sql = ""
        params: list[Any] = []

        if company_id:
            where_sql = "WHERE company_id = $1"
            params.append(company_id)

        summary_sql = f"""
            SELECT
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COUNT(*) FILTER (WHERE input_mode = 'text') AS total_text,
                COUNT(*) FILTER (WHERE input_mode = 'audio') AS total_audio
            FROM interactions
            {where_sql}
        """

        latest_sql = f"""
            SELECT
                session_id,
                company_id,
                turn_index,
                input_mode,
                question,
                response,
                language_detected,
                llm_provider_used,
                latency_total_s,
                created_at
            FROM interactions
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ${len(params) + 1}
        """

        async with _pool.acquire() as conn:
            summary_row = await conn.fetchrow(summary_sql, *params)
            latest_rows = await conn.fetch(latest_sql, *params, safe_limit)

        summary = {
            "total_sessions": int(summary_row["total_sessions"] or 0),
            "total_interactions": int(summary_row["total_interactions"] or 0),
            "total_text": int(summary_row["total_text"] or 0),
            "total_audio": int(summary_row["total_audio"] or 0),
        }

        latest_interactions = []
        for row in latest_rows:
            latest_interactions.append(
                {
                    "session_id": row["session_id"],
                    "company_id": row["company_id"],
                    "turn_index": row["turn_index"],
                    "input_mode": row["input_mode"],
                    "question": row["question"],
                    "response": row["response"],
                    "language_detected": row["language_detected"],
                    "llm_provider_used": row["llm_provider_used"],
                    "latency_total_s": float(row["latency_total_s"] or 0),
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
            )

        return {
            "summary": summary,
            "latest_interactions": latest_interactions,
        }
