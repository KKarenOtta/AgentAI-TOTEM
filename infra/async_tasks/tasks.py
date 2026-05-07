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
