"""Reporting utilities for RAG evaluation results.

This module is responsible ONLY for presenting and persisting
evaluation results. It contains no metric calculation or pipeline
orchestration logic.
"""

from pathlib import Path

import pandas as pd

from evaluation.evaluator import EvaluationResult, EvaluationSummary


def print_summary(summary: EvaluationSummary) -> None:
    """Print a formatted evaluation summary to stdout.

    Args:
        summary: The aggregated evaluation summary to display.
    """
    separator = "-" * 36
    print(separator)
    print(f"Questions evaluated: {summary.questions_evaluated}")
    print(f"Recall@K: {summary.recall_at_k:.2f}")
    print(f"MRR: {summary.mrr:.2f}")
    print(f"Faithfulness: {summary.faithfulness:.2f}")
    print(f"Answer Relevance: {summary.answer_relevance:.2f}")
    print(f"Average Latency: {summary.average_latency_seconds:.2f}s")
    print(separator)


def write_csv_report(results: list[EvaluationResult], output_path: Path) -> None:
    """Write per-question evaluation results to a CSV file.

    Args:
        results: Per-question evaluation results to persist.
        output_path: Destination path for the CSV report.
    """
    rows = [result.model_dump() for result in results]
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(output_path, index=False)
