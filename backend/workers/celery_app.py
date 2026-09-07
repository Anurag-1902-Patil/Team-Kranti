"""
Celery application configuration.
Broker: Redis. Result backend: Redis.
Retry policy: 3 attempts with exponential backoff (60s → 120s → 240s).
"""

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sih26122",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,
    # Task behavior
    task_acks_late=True,               # ACK only after successful processing
    task_reject_on_worker_lost=True,   # Re-queue if worker dies mid-task
    worker_prefetch_multiplier=1,      # One task at a time per worker (predictable)
    # Retry defaults (overridden per-task where needed)
    task_max_retries=3,
    # Result expiry
    result_expires=86400,              # 24 hours
    # Soft/hard time limits for tasks
    task_soft_time_limit=300,          # 5 minutes soft (sends SIGTERM)
    task_time_limit=600,               # 10 minutes hard (sends SIGKILL)
)
