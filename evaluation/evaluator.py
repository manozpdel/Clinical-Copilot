"""Evaluation pipeline orchestration for the RAG system."""

import time

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from evaluation.dataset import QAItem
from evaluation.judge import score_answer_relevance, score_faithfulness
from evaluation.metrics import mean_reciprocal_rank, recall_at_k
from llm.client import (
    build_faithfulness_client,
    build_generation_client,
    build_relevance_client,
)
from llm.generator import generate_answer
from llm.prompts import build_context

logger = get_logger(__name__)


class EvaluationResult(BaseModel):
    """Evaluation metrics for a single QA pair.

    Attributes:
        question: The evaluated question.
        recall_at_k: Binary Recall@K for the relevant chunk.
        reciprocal_rank: Reciprocal rank of the relevant chunk.
        faithfulness: Faithfulness score of the generated answer.
        answer_relevance: Relevance score of the generated answer.
        latency_seconds: Wall-clock time taken to answer the question.
    """

    question: str
    recall_at_k: float
    reciprocal_rank: float
    faithfulness: float
    answer_relevance: float
    latency_seconds: float


class EvaluationSummary(BaseModel):
    """Aggregate evaluation metrics across an entire QA dataset.

    Attributes:
        questions_evaluated: Number of QA pairs evaluated.
        recall_at_k: Mean Recall@K across all questions.
        mrr: Mean Reciprocal Rank across all questions.
        faithfulness: Mean faithfulness score across all questions.
        answer_relevance: Mean answer relevance score across all
            questions.
        average_latency_seconds: Mean answer generation latency across
            all questions.
    """

    questions_evaluated: int
    recall_at_k: float
    mrr: float
    faithfulness: float
    answer_relevance: float
    average_latency_seconds: float


def evaluate_single_item(
    item: QAItem,
    generation_client,
    faithfulness_client,
    relevance_client,
    settings: Settings,
) -> EvaluationResult:
    """Evaluate a single QA pair using three independent Groq clients.

    Args:
        item: The QA pair to evaluate.
        generation_client: GroqClient configured for answer generation.
        faithfulness_client: GroqClient configured for faithfulness
            judging.
        relevance_client: GroqClient configured for relevance judging.
        settings: Active application settings.

    Returns:
        EvaluationResult: The computed metrics for this QA pair.
    """
    result = generate_answer(item.question, client=generation_client, settings=settings)

    retrieved_chunk_ids = [chunk.chunk_id for chunk in result.context_chunks]
    recall = recall_at_k(retrieved_chunk_ids, item.relevant_chunk_id)
    reciprocal_rank = mean_reciprocal_rank(retrieved_chunk_ids, item.relevant_chunk_id)

    context = build_context(result.context_chunks)
    faithfulness = score_faithfulness(context, result.answer, faithfulness_client)
    answer_relevance = score_answer_relevance(
        item.question, result.answer, relevance_client
    )

    return EvaluationResult(
        question=item.question,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        latency_seconds=result.latency_seconds,
    )


def aggregate_results(results: list[EvaluationResult]) -> EvaluationSummary:
    """Aggregate per-question evaluation results into a summary.

    Args:
        results: Per-question evaluation results.

    Returns:
        EvaluationSummary: The aggregated evaluation summary.
    """
    count = len(results)
    if count == 0:
        return EvaluationSummary(
            questions_evaluated=0,
            recall_at_k=0.0,
            mrr=0.0,
            faithfulness=0.0,
            answer_relevance=0.0,
            average_latency_seconds=0.0,
        )

    return EvaluationSummary(
        questions_evaluated=count,
        recall_at_k=sum(r.recall_at_k for r in results) / count,
        mrr=sum(r.reciprocal_rank for r in results) / count,
        faithfulness=sum(r.faithfulness for r in results) / count,
        answer_relevance=sum(r.answer_relevance for r in results) / count,
        average_latency_seconds=sum(r.latency_seconds for r in results) / count,
    )


def run_evaluation(
    dataset: list[QAItem], settings: Settings | None = None
) -> tuple[list[EvaluationResult], EvaluationSummary]:
    """Run the full evaluation pipeline over a QA dataset.

    Instantiates three independent Groq clients, one per pipeline role,
    each using its own API key and rate-limit quota.

    Args:
        dataset: The QA pairs to evaluate.
        settings: Optional application settings override.

    Returns:
        tuple[list[EvaluationResult], EvaluationSummary]: Per-question
            results and the aggregated summary.
    """
    active_settings = settings or get_settings()
    generation_client = build_generation_client(active_settings)
    faithfulness_client = build_faithfulness_client(active_settings)
    relevance_client = build_relevance_client(active_settings)

    logger.info("evaluation_started", question_count=len(dataset))
    start_time = time.monotonic()

    results = [
        evaluate_single_item(
            item,
            generation_client,
            faithfulness_client,
            relevance_client,
            active_settings,
        )
        for item in dataset
    ]

    summary = aggregate_results(results)
    elapsed = time.monotonic() - start_time
    logger.info(
        "evaluation_completed", question_count=len(dataset), elapsed_seconds=elapsed
    )

    return results, summary
