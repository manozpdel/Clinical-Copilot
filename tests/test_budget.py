"""Tests for token/cost estimation."""

from security.budget import calculate_cost, estimate_tokens, estimate_usage


def test_estimate_tokens_scales_with_length() -> None:
    """Longer text should estimate to more tokens."""
    short_count = estimate_tokens("hello")
    long_count = estimate_tokens("hello " * 100)

    assert long_count > short_count


def test_estimate_tokens_empty_string_is_zero() -> None:
    """An empty string should estimate to zero tokens."""
    assert estimate_tokens("") == 0


def test_calculate_cost_uses_known_model_pricing() -> None:
    """A known model should produce a positive, deterministic cost."""
    cost = calculate_cost("llama-3.3-70b-versatile", 1000, 500)

    assert cost > 0


def test_calculate_cost_falls_back_for_unknown_model() -> None:
    """An unrecognized model should still produce a positive cost."""
    cost = calculate_cost("some-unknown-model", 1000, 500)

    assert cost > 0


def test_estimate_usage_returns_consistent_totals() -> None:
    """total_tokens should equal prompt_tokens + completion_tokens."""
    usage = estimate_usage(
        "llama-3.1-8b-instant", "What medications?", "Metformin 500mg."
    )

    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens
    assert usage.cost_usd >= 0
