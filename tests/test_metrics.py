"""Tests for retrieval evaluation metrics."""

from evaluation.metrics import mean_reciprocal_rank, recall_at_k


def test_recall_at_k_hit() -> None:
    """Recall@K should return 1.0 when the relevant chunk is retrieved."""
    assert recall_at_k(["a", "b", "c"], "b") == 1.0


def test_recall_at_k_miss() -> None:
    """Recall@K should return 0.0 when the relevant chunk is missing."""
    assert recall_at_k(["a", "b", "c"], "z") == 0.0


def test_mean_reciprocal_rank_first_position() -> None:
    """MRR should return 1.0 when the relevant chunk ranks first."""
    assert mean_reciprocal_rank(["a", "b", "c"], "a") == 1.0


def test_mean_reciprocal_rank_third_position() -> None:
    """MRR should return the correct reciprocal rank for later positions."""
    assert mean_reciprocal_rank(["a", "b", "c"], "c") == 1.0 / 3


def test_mean_reciprocal_rank_not_found() -> None:
    """MRR should return 0.0 when the relevant chunk is not retrieved."""
    assert mean_reciprocal_rank(["a", "b", "c"], "z") == 0.0
