"""Tests for the evaluation aggregation pipeline."""

from evaluation.evaluator import EvaluationResult, aggregate_results


def _result(
    recall: float,
    reciprocal_rank: float,
    faithfulness: float,
    relevance: float,
    latency: float,
) -> EvaluationResult:
    """Build a sample evaluation result for use in aggregation tests.

    Args:
        recall: Recall@K value.
        reciprocal_rank: Reciprocal rank value.
        faithfulness: Faithfulness score.
        relevance: Answer relevance score.
        latency: Latency in seconds.

    Returns:
        EvaluationResult: A representative evaluation result.
    """
    return EvaluationResult(
        question="sample question",
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        faithfulness=faithfulness,
        answer_relevance=relevance,
        latency_seconds=latency,
    )


def test_aggregate_results_computes_averages() -> None:
    """Aggregation should compute correct averages across all results."""
    results = [
        _result(1.0, 1.0, 0.8, 0.9, 1.0),
        _result(0.0, 0.0, 0.6, 0.7, 3.0),
    ]

    summary = aggregate_results(results)

    assert summary.questions_evaluated == 2
    assert summary.recall_at_k == 0.5
    assert summary.mrr == 0.5
    assert summary.faithfulness == 0.7
    assert summary.answer_relevance == 0.8
    assert summary.average_latency_seconds == 2.0


def test_aggregate_results_handles_empty_list() -> None:
    """Aggregation should return zeroed metrics for an empty result list."""
    summary = aggregate_results([])

    assert summary.questions_evaluated == 0
    assert summary.recall_at_k == 0.0
    assert summary.mrr == 0.0
    assert summary.faithfulness == 0.0
    assert summary.answer_relevance == 0.0
    assert summary.average_latency_seconds == 0.0