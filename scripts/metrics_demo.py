"""CLI entry point that records sample metrics and prints the exposition text."""

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


def main() -> None:
    """Record representative sample metrics and print the exposition text."""
    record_request("POST", "/api/query", 200, 0.85)
    record_llm_latency("llama-3.3-70b-versatile", 0.62)
    record_llm_tokens("llama-3.3-70b-versatile", prompt_tokens=120, completion_tokens=45)
    record_retriever_latency(0.04)
    record_tool_latency("ehr", 0.01)
    record_voice_transcription_latency(1.2)
    record_node_duration("planner", 0.001)
    record_node_duration("generator", 0.6)

    print(generate_latest().decode("utf-8"))


if __name__ == "__main__":
    main()
