"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

# Set flag to use NullPool for Celery workers
# This prevents connection pool sharing issues across processes
settings._USE_NULL_POOL = True

# Create Celery instance
# Explicitly specify broker_transport to ensure Redis is used
celery_app = Celery(
    "email_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks"],
)
# Explicitly set broker transport to redis (not amqp/pyamqp)
celery_app.conf.broker_transport = 'redis'

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Explicitly set broker transport to redis
    broker_transport_options={
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        }
    },
    # Ensure Redis is used as broker
    broker_connection_retry_on_startup=True,
)

# Scheduled tasks (beat schedule)
celery_app.conf.beat_schedule = {
    "fetch-all-accounts-emails": {
        "task": "fetch_all_accounts_emails",
        "schedule": 300.0,  # Every 5 minutes
    },
}

