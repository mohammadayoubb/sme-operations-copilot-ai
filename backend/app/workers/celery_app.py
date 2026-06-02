from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "soukpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.invoice_tasks",
        "app.workers.indexing_tasks",
        "app.workers.report_tasks",
        "app.workers.forecast_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Beirut",
    enable_utc=True,
    task_routes={
        "app.workers.invoice_tasks.*": {"queue": "ocr"},
        "app.workers.indexing_tasks.*": {"queue": "indexing"},
        "app.workers.report_tasks.*": {"queue": "reports"},
        "app.workers.forecast_tasks.*": {"queue": "forecasting"},
    },
)

celery_app.conf.beat_schedule = {
    "weekly-report-monday-8am": {
        "task": "app.workers.report_tasks.generate_weekly_report",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    "retrain-forecast-weekly": {
        "task": "app.workers.forecast_tasks.retrain_forecasting_model",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
    },
}
