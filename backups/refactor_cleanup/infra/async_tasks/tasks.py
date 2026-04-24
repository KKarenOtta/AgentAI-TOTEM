from services.async_tasks.celery_app import celery

# =========================
# LOG
# =========================
@celery.task(name="tasks.log_training")
def log_training_task(session_id, question, answer, score):
    from services.semantic.history_logger import log_turn
    log_turn(session_id, question, answer, score)


# =========================
# DATASET
# =========================
@celery.task(name="tasks.build_dataset")
def build_dataset():
    from services.semantic.dataset_builder import build
    build()
    return "dataset built"


# =========================
# FINE TUNE
# =========================
@celery.task(name="tasks.fine_tune")
def fine_tune():
    from services.semantic.fine_tune import train
    train()
    return "model trained"


# =========================
# OPTIMIZER
# =========================
@celery.task(name="tasks.optimize")
def optimize():
    from services.semantic.optimizer import optimize
    optimize()
    return "threshold optimized"


# =========================
# EVALUATOR
# =========================
@celery.task(name="tasks.evaluate")
def evaluate():
    from services.semantic.evaluator import evaluate
    evaluate()
    return "quality evaluated"


# =========================
# REBUILD EMBEDDINGS
# =========================
@celery.task(name="tasks.rebuild_embeddings")
def rebuild_embeddings():
    from services.semantic.faq_engine import FAQEngine
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
