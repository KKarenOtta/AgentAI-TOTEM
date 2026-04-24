from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "totem",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["infra.async_tasks.tasks"]
)

# =========================
# SCHEDULE AUTOMÁTICO
# =========================
celery.conf.beat_schedule = {

    # pipeline completo a cada 1 hora
    "full-pipeline-hourly": {
        "task": "tasks.full_pipeline",
        "schedule": crontab(minute=0, hour="*"),
    },

    # avaliação rápida a cada 10 min
    "evaluation-fast": {
        "task": "tasks.evaluate",
        "schedule": crontab(minute="*/10"),
    },

    # otimização leve a cada 30 min
    "optimize-mid": {
        "task": "tasks.optimize",
        "schedule": crontab(minute="*/30"),
    },
}

celery.conf.timezone = "America/Sao_Paulo"
