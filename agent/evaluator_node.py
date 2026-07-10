"""Answer evaluation logic for the Clinical Copilot agent.

This module is responsible ONLY for scoring the generated answer using
the existing evaluation layer (Part 4). It contains no retrieval or
generation logic, and reuses `evaluation.judge.score_faithfulness`
rather than reimplementing faithfulness scoring. Evaluation never
halts or alters graph execution; it only records results.
"""

from typing import Any

from evaluation.judge import score_faithfulness
from llm.client import GroqClient


def evaluate_response(
    context: str,
    answer: str,
    citations: list[str],
    client: GroqClient,
    enable_evaluation: bool,
) -> dict[str, Any]:
    """Evaluate a generated answer for faithfulness and citation coverage.

    Args:
        context: The formatted context the answer should be grounded
            in.
        answer: The generated answer, with citations appended.
        citations: The extracted citation strings supporting the
            answer.
        client: GroqClient used to perform LLM-as-a-judge faithfulness
            scoring.
        enable_evaluation: Whether to run the LLM-based faithfulness
            judge. When False, faithfulness scoring is skipped and
            reported as unavailable, while citation/context checks
            still run.

    Returns:
        dict[str, Any]: Evaluation results containing `faithfulness`
            (float or None when skipped), `citation_present` (bool),
            and `context_used` (bool).
    """
    citation_present = bool(citations)
    context_used = bool(context.strip()) and citation_present

    faithfulness: float | None = None
    if enable_evaluation:
        faithfulness = score_faithfulness(context, answer, client)

    return {
        "faithfulness": faithfulness,
        "citation_present": citation_present,
        "context_used": context_used,
    }
