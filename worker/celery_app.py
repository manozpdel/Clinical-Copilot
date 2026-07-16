"""Celery application factory and beat schedule.

Responsible ONLY for Celery configuration (broker, backend, retry
policy, task routing, beat schedule). Task bodies live in `tasks.py`.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "clinical_copilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=max(settings.celery_task_time_limit - 30, 30),
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_max_retries=settings.celery_task_max_retries,
    task_routes={
        "worker.tasks.run_evaluation_task": {"queue": "evaluation"},
        "worker.tasks.generate_embeddings_task": {"queue": "embeddings"},
        "worker.tasks.cleanup_task": {"queue": "maintenance"},
        "worker.tasks.compute_analytics_task": {"queue": "analytics"},
    },
    beat_schedule={
        "periodic-cleanup": {
            "task": "worker.tasks.cleanup_task",
            "schedule": crontab(minute=0, hour=f"*/{settings.celery_beat_cleanup_schedule_hours}"),
        },
        "periodic-analytics-refresh": {
            "task": "worker.tasks.compute_analytics_task",
            "schedule": crontab(minute=30, hour="*/6"),
        },
        "periodic-quota-reset-check": {
            "task": "worker.tasks.reset_quotas_task",
            "schedule": crontab(minute=0, hour=0),
        },
    },
)
