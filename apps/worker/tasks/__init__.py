"""Celery tasks — thin wrappers around pipeline functions."""

from celery_app import celery
from pipeline.embed import embed_new_documents as _embed
from pipeline.ingest import run_all_connectors as _run_all


@celery.task(name="tasks.run_all_connectors")
def run_all_connectors() -> dict:
    return _run_all()


@celery.task(name="tasks.embed_new_documents")
def embed_new_documents() -> dict:
    return _embed()


@celery.task(name="tasks.generate_weekly_report")
def generate_weekly_report() -> dict:
    # Implemented in milestone M9 (weekly report generator).
    return {"status": "noop", "stage": "weekly_report"}
