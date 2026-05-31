"""Celery Beat schedule — daily ingestion + weekly analytics/report."""

from celery.schedules import crontab

beat_schedule = {
    "daily-ingestion": {
        "task": "tasks.run_all_connectors",
        "schedule": crontab(hour=4, minute=0),  # 04:00 UTC daily
    },
    "daily-embeddings": {
        "task": "tasks.embed_new_documents",
        "schedule": crontab(hour=5, minute=0),
    },
    "daily-analytics": {
        "task": "tasks.compute_analytics",
        "schedule": crontab(hour=5, minute=30),  # after embeddings
    },
    "weekly-report": {
        "task": "tasks.generate_weekly_report",
        "schedule": crontab(hour=6, minute=0, day_of_week="monday"),
    },
}
