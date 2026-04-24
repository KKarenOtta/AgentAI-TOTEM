from infra.async_tasks.celery_app import celery

# =========================
# LOG
# =========================
@celery.task(name="tasks.log_training")
def log_training_task(session_id, question, answer, score):
    from ml.semantic.history_logger import log_turn
    log_turn(session_id, question, answer, score)


# =========================
# DATASET
# =========================
@celery.task(name="tasks.build_dataset")
def build_dataset():
    from ml.semantic.dataset_builder import build
    build()
    return "dataset built"


# =========================
# FINE TUNE
# =========================
@celery.task(name="tasks.fine_tune")
def fine_tune():
    from ml.semantic.fine_tune import train
    train()
    return "model trained"


# =========================
# OPTIMIZER
# =========================
@celery.task(name="tasks.optimize")
def optimize():
    from ml.semantic.optimizer import optimize
    optimize()
    return "threshold optimized"


# =========================
# EVALUATOR
# =========================
@celery.task(name="tasks.evaluate")
def evaluate():
    from ml.semantic.evaluator import evaluate
    evaluate()
    return "quality evaluated"


# =========================
# REBUILD EMBEDDINGS
# =========================
@celery.task(name="tasks.rebuild_embeddings")
def rebuild_embeddings():
    from ml.semantic.faq_engine import FAQEngine
    FAQEngine()
    return "embeddings rebuilt"


# =========================
# PIPELINE COMPLETO
# =========================
@celery.task(name="tasks.full_pipeline")
def full_pipeline():
    build_dataset.delay()
    fine_tune.delay()
    optimize.delay()
    evaluate.delay()
    rebuild_embeddings.delay()
    return "pipeline triggered"
