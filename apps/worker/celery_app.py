import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery("bos", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Register tasks explicitly to avoid module-path issues in container startup.
import tasks  # noqa: F401,E402

# Register the daily schedule.
from beat_schedule import beat_schedule  # noqa: E402

celery.conf.beat_schedule = beat_schedule
