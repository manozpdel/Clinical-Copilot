"""Tests for Prometheus metrics recording."""

from prometheus_client import generate_latest

from observability.metrics import (
    record_llm_latency,
    record_llm_tokens,
    record_node_duration,
    record_request,
    record_retriever_latency,
    record_tool_latency,
    record_voice_transcription_latency,
)


def test_record_request_appears_in_exposition() -> None:
    """A recorded request should appear in the Prometheus exposition text."""
    record_request("GET", "/api/health", 200, 0.01)

    output = generate_latest().decode("utf-8")

    assert "http_requests_total" in output
    assert "http_request_duration_seconds" in output


def test_record_llm_latency_and_tokens_appear_in_exposition() -> None:
    """LLM latency and token metrics should appear in the exposition text."""
    record_llm_latency("llama-3.3-70b-versatile", 0.5)
    record_llm_tokens("llama-3.3-70b-versatile", prompt_tokens=10, completion_tokens=5)

    output = generate_latest().decode("utf-8")

    assert "llm_call_duration_seconds" in output
    assert "llm_tokens_total" in output


def test_record_retriever_tool_and_voice_latency_appear_in_exposition() -> None:
    """Retriever, tool, and voice latency metrics should be exposed."""
    record_retriever_latency(0.02)
    record_tool_latency("ehr", 0.01)
    record_voice_transcription_latency(1.0)

    output = generate_latest().decode("utf-8")

    assert "retriever_query_duration_seconds" in output
    assert "tool_execution_duration_seconds" in output
    assert "voice_transcription_duration_seconds" in output


def test_record_node_duration_appears_in_exposition() -> None:
    """LangGraph node duration metrics should be exposed."""
    record_node_duration("planner", 0.001)

    output = generate_latest().decode("utf-8")

    assert "langgraph_node_duration_seconds" in output
