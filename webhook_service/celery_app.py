from celery import Celery
from .config import Config
from celery.schedules import crontab

celery_app = Celery(
    'webhook_service_tasks',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=['webhook_service.tasks']
)

celery_app.conf.update(
    task_serializer=Config.CELERY_TASK_SERIALIZER,
    result_serializer=Config.CELERY_RESULT_SERIALIZER,
    accept_content=Config.CELERY_ACCEPT_CONTENT,
    timezone=Config.CELERY_TIMEZONE,
    enable_utc=Config.CELERY_ENABLE_UTC,
    task_ignore_result=Config.CELERY_TASK_IGNORE_RESULT,
    task_track_started=Config.CELERY_TASK_TRACK_STARTED,
    beat_schedule={
        'cleanup-old-logs': {
            'task': 'webhook_service.tasks.cleanup_old_logs',
            'schedule': crontab(minute='0', hour='*/6'),
            'args': (),
        },
    },
)
