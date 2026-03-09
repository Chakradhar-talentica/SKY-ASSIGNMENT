"""
Celery application configuration.
"""
from celery import Celery
from src.config.settings import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "skyhigh_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.domains.seats.tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-holds": {
            "task": "cleanup_expired_holds",
            "schedule": 30.0,  # Every 30 seconds
        },
    },
)


# Optional: Configure task routes
celery_app.conf.task_routes = {
    "expire_seat_hold": {"queue": "seats"},
    "cleanup_expired_holds": {"queue": "seats"},
}

