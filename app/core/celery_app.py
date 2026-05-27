from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "soccer_telemetry",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["app.workers"])

celery_app.conf.beat_schedule = {
    "process-telemetry-batch": {
        "task": "app.workers.tasks.process_batch_task",
        "schedule": 2.0,
    },
}
