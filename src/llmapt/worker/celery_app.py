"""Celery application configured without starting network activity on import."""

from celery import Celery

from llmapt.config import get_settings

settings = get_settings()

celery_app = Celery(
    "llmapt",
    broker=settings.broker_url,
    backend=settings.redis_url,
    include=["llmapt.worker.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_expires=3600,
    task_acks_late=True,
    task_default_queue="control",
    task_reject_on_worker_lost=True,
    task_serializer="json",
    timezone="UTC",
    worker_cancel_long_running_tasks_on_connection_loss=True,
    worker_enable_remote_control=False,
    worker_prefetch_multiplier=1,
)
