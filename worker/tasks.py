"""Celery task definitions.

Each task is a thin async-to-sync bridge around existing pure business
logic (evaluation, ingestion, feedback analytics, quota reset). No
task duplicates logic already implemented in earlier milestones.
"""

import asyncio

from celery.utils.log import get_task_logger

from database.crud import reset_all_quotas
from database.session import SessionLocal
from evaluation.dataset import generate_qa_dataset
from evaluation.evaluator import run_evaluation
from feedback.analytics import compute_analytics
from ingest.ingest import run_ingestion
from worker.celery_app import celery_app

logger = get_task_logger(__name__)


def _run_async(coro):
    """Run an async coroutine to completion inside a synchronous Celery task."""
    return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_evaluation_task(self, sample_size: int = 10) -> dict:
    """Run the RAG evaluation harness as a background job.

    Args:
        sample_size: Number of QA pairs to sample for this run.

    Returns:
        dict: Aggregated evaluation summary.
    """
    try:
        dataset = generate_qa_dataset()[:sample_size]
        _results, summary = _run_async(_evaluate(dataset))
        logger.info("evaluation_task_complete", extra={"count": len(dataset)})
        return summary.model_dump()
    except Exception as error:  # noqa: BLE001
        raise self.retry(exc=error) from error


async def _evaluate(dataset):
    """Run evaluation asynchronously; kept separate for asyncio.run compatibility."""
    return await asyncio.get_event_loop().run_in_executor(None, run_evaluation, dataset)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_embeddings_task(self) -> dict:
    """Regenerate the synthetic patient corpus and re-ingest it into Chroma.

    Returns:
        dict: Ingestion summary (patients generated, chunks, embeddings).
    """
    try:
        summary = run_ingestion()
        logger.info("embeddings_task_complete", extra={"chunks": summary.chunks_created})
        return summary.__dict__
    except Exception as error:  # noqa: BLE001
        raise self.retry(exc=error) from error


@celery_app.task
def cleanup_task() -> str:
    """Periodic maintenance placeholder for future extensibility.

    Currently a no-op that logs a heartbeat; reserved for future
    stale-session/temp-file cleanup without requiring a task-routing
    change downstream.

    Returns:
        str: Status message.
    """
    logger.info("cleanup_task_ran")
    return "ok"


@celery_app.task
def compute_analytics_task() -> dict:
    """Recompute feedback analytics as a background job.

    Returns:
        dict: The computed analytics summary.
    """

    async def _compute() -> dict:
        async with SessionLocal() as db:
            summary = await compute_analytics(db)
            return summary.model_dump()

    result = _run_async(_compute())
    logger.info("analytics_task_complete")
    return result


@celery_app.task
def reset_quotas_task() -> int:
    """Force-reset all user quota counters (safety net alongside lazy reset).

    Returns:
        int: Number of quota records reset.
    """

    async def _reset() -> int:
        async with SessionLocal() as db:
            return await reset_all_quotas(db)

    count = _run_async(_reset())
    logger.info("quota_reset_task_complete", extra={"count": count})
    return count