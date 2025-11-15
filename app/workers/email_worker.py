"""Email worker - Celery worker entry point.

This file is kept for backward compatibility.
The actual email fetching tasks are in app.tasks.email_tasks
"""

# This file can be used to start Celery worker:
# celery -A app.workers.email_worker worker --loglevel=info

from app.core.celery_app import celery_app

__all__ = ["celery_app"]
