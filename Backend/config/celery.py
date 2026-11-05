import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("social_publisher")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "scan-due-posts-every-60s": {
        "task": "platforms.tasks.scan_due_posts",
        "schedule": 60.0,
    },
    "refresh-credentials-every-30min": {
        "task": "platforms.tasks.refresh_expiring_credentials",
        "schedule": crontab(minute="*/30"),
    },
}