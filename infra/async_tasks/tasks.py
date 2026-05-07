from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from infra.async_tasks.celery_app import celery


@celery.task(name="tasks.log_training")
def log_training_task(session_id, question, answer, score):
    from ml.semantic.history_logger import log_turn

    log_turn(session_id, question, answer, score)


@celery.task(name="tasks.build_dataset")
def build_dataset():
    from ml.semantic.dataset_builder import build

    build()
    return "dataset built"


@celery.task(name="tasks.fine_tune")
def fine_tune():
    from ml.semantic.fine_tune import train

    train()
    return "model trained"


@celery.task(name="tasks.optimize")
def optimize():
    from ml.semantic.optimizer import optimize

    optimize()
    return "threshold optimized"


@celery.task(name="tasks.evaluate")
def evaluate():
    from ml.semantic.evaluator import evaluate

    evaluate()
    return "quality evaluated"


@celery.task(name="tasks.rebuild_embeddings")
def rebuild_embeddings():
    from ml.semantic.faq_engine import FAQEngine

    FAQEngine()
    return "embeddings rebuilt"


@celery.task(name="tasks.full_pipeline")
def full_pipeline():
    build_dataset.delay()
    fine_tune.delay()
    optimize.delay()
    evaluate.delay()
    rebuild_embeddings.delay()

    return "pipeline triggered"


@celery.task(name="tasks.sync_pending_events")
def sync_pending_events(limit: int = 100):
    import asyncio

    from app.services.aws_db_service import AWSDBService, close_db_pool, init_db_pool
    from core.persistence.sync_queue import list_pending, mark_failed, mark_synced

    async def _run():
        await init_db_pool()

        db = AWSDBService()
        rows = list_pending(limit=limit)

        synced = 0
        failed = 0
        skipped = 0

        for row in rows:
            sync_id = row.get("sync_id")
            entity = row.get("entity")
            payload = row.get("payload") or {}

            try:
                if entity == "metrics":
                    await db.insert_metric(payload)
                elif entity == "lead":
                    await db.upsert_lead(payload)
                elif entity == "consent":
                    await db.insert_consent(payload)
                else:
                    skipped += 1
                    mark_failed(sync_id, f"unknown_entity:{entity}")
                    continue

                mark_synced(sync_id)
                synced += 1

                try:
                    await db.record_sync_audit(row, status="synced")
                except Exception:
                    pass

            except Exception as exc:
                failed += 1
                error = f"{type(exc).__name__}: {exc}"
                mark_failed(sync_id, error)

                try:
                    await db.record_sync_audit(row, status="failed", error=error)
                except Exception:
                    pass

        await close_db_pool()

        return {
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "total": len(rows),
        }

    return asyncio.run(_run())
