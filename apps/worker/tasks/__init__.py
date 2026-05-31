"""Celery tasks — thin wrappers around pipeline functions."""

from analytics.report import build_weekly_report as _report
from celery_app import celery
from pipeline.embed import embed_new_documents as _embed
from pipeline.ingest import run_all_connectors as _run_all
from pipeline.linkage import build_linkage_graph as _linkage
from pipeline.run_analytics import run_analytics as _analytics
from pipeline.tag import tag_documents as _tag


@celery.task(name="tasks.run_all_connectors")
def run_all_connectors() -> dict:
    return _run_all()


@celery.task(name="tasks.tag_documents")
def tag_documents() -> dict:
    return _tag()


@celery.task(name="tasks.build_linkage_graph")
def build_linkage_graph() -> dict:
    return _linkage()


@celery.task(name="tasks.embed_new_documents")
def embed_new_documents() -> dict:
    return _embed()


@celery.task(name="tasks.compute_analytics")
def compute_analytics() -> dict:
    return _analytics()


@celery.task(name="tasks.generate_weekly_report")
def generate_weekly_report() -> dict:
    return _report()
