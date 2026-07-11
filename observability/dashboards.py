"""Reusable helpers for future Grafana dashboards.

This module is responsible ONLY for describing metric labels and panel
definitions that a Grafana dashboard (or similar tool) could consume.
It contains no metric recording, tracing, or health-check logic.
"""

from typing import Any

METRIC_NAMES: tuple[str, ...] = (
    "http_requests_total",
    "http_errors_total",
    "http_request_duration_seconds",
    "llm_call_duration_seconds",
    "llm_tokens_total",
    "retriever_query_duration_seconds",
    "database_query_duration_seconds",
    "tool_execution_duration_seconds",
    "voice_transcription_duration_seconds",
    "langgraph_node_duration_seconds",
)


def build_metric_labels(**kwargs: Any) -> dict[str, str]:
    """Build a clean label dictionary for a Prometheus query, dropping Nones.

    Args:
        **kwargs: Candidate label key/value pairs.

    Returns:
        dict[str, str]: Only the non-None labels, stringified.
    """
    return {key: str(value) for key, value in kwargs.items() if value is not None}


def recommended_dashboard_panels() -> list[dict[str, Any]]:
    """Describe a recommended set of Grafana panels for this application.

    Returns:
        list[dict[str, Any]]: Panel definitions (title, target metric,
            and visualization type) suitable for hand-authoring a
            Grafana dashboard JSON model in a later milestone.
    """
    return [
        {"title": "Request Rate", "metric": "http_requests_total", "type": "graph"},
        {"title": "Error Rate", "metric": "http_errors_total", "type": "graph"},
        {"title": "Request Latency (p95)", "metric": "http_request_duration_seconds", "type": "heatmap"},
        {"title": "LLM Call Latency", "metric": "llm_call_duration_seconds", "type": "graph"},
        {"title": "Token Usage", "metric": "llm_tokens_total", "type": "graph"},
        {"title": "Retriever Latency", "metric": "retriever_query_duration_seconds", "type": "graph"},
        {"title": "Database Latency", "metric": "database_query_duration_seconds", "type": "graph"},
        {"title": "Tool Execution Latency", "metric": "tool_execution_duration_seconds", "type": "graph"},
        {"title": "Voice Transcription Latency", "metric": "voice_transcription_duration_seconds", "type": "graph"},
        {"title": "LangGraph Node Duration", "metric": "langgraph_node_duration_seconds", "type": "graph"},
    ]
