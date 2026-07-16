"""Prometheus metrics collection.

This module is responsible ONLY for defining and recording Prometheus
metrics. It contains no logging, tracing, or health-check logic.
"""

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests.", ["method", "path", "status"])
ERROR_COUNT = Counter(
    "http_errors_total", "Total HTTP requests resulting in an error.", ["method", "path"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request duration.", ["method", "path"]
)

LLM_LATENCY = Histogram("llm_call_duration_seconds", "Groq LLM call duration.", ["model"])
LLM_TOKENS = Counter("llm_tokens_total", "Total LLM tokens consumed.", ["model", "token_type"])
RETRIEVER_LATENCY = Histogram(
    "retriever_query_duration_seconds", "Chroma retriever query duration."
)
DATABASE_LATENCY = Histogram("database_query_duration_seconds", "Database query duration.")
TOOL_LATENCY = Histogram(
    "tool_execution_duration_seconds", "Mock clinical tool execution duration.", ["tool_name"]
)
VOICE_TRANSCRIPTION_LATENCY = Histogram(
    "voice_transcription_duration_seconds", "Groq Whisper transcription duration."
)
NODE_DURATION = Histogram(
    "langgraph_node_duration_seconds", "LangGraph node execution duration.", ["node_name"]
)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record a completed HTTP request.

    Args:
        method: The HTTP method used.
        path: The request path (route template preferred over raw URL).
        status_code: The response's HTTP status code.
        duration_seconds: Wall-clock time taken to handle the request.
    """
    REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration_seconds)
    if status_code >= 500:
        ERROR_COUNT.labels(method=method, path=path).inc()


def record_error(method: str, path: str) -> None:
    """Record an unhandled exception during request handling.

    Args:
        method: The HTTP method used.
        path: The request path.
    """
    ERROR_COUNT.labels(method=method, path=path).inc()


def record_llm_latency(model: str, duration_seconds: float) -> None:
    """Record the duration of a single Groq LLM call.

    Args:
        model: Name of the Groq model used.
        duration_seconds: Wall-clock time the call took.
    """
    LLM_LATENCY.labels(model=model).observe(duration_seconds)


def record_llm_tokens(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Record token usage for a single Groq LLM call.

    Args:
        model: Name of the Groq model used.
        prompt_tokens: Number of prompt tokens consumed.
        completion_tokens: Number of completion tokens consumed.
    """
    LLM_TOKENS.labels(model=model, token_type="prompt").inc(prompt_tokens)
    LLM_TOKENS.labels(model=model, token_type="completion").inc(completion_tokens)


def record_retriever_latency(duration_seconds: float) -> None:
    """Record the duration of a single Chroma retriever query.

    Args:
        duration_seconds: Wall-clock time the query took.
    """
    RETRIEVER_LATENCY.observe(duration_seconds)


def record_database_latency(duration_seconds: float) -> None:
    """Record the duration of a single database query.

    Args:
        duration_seconds: Wall-clock time the query took.
    """
    DATABASE_LATENCY.observe(duration_seconds)


def record_tool_latency(tool_name: str, duration_seconds: float) -> None:
    """Record the duration of a single mock clinical tool execution.

    Args:
        tool_name: Name of the executed tool.
        duration_seconds: Wall-clock time the execution took.
    """
    TOOL_LATENCY.labels(tool_name=tool_name).observe(duration_seconds)


def record_voice_transcription_latency(duration_seconds: float) -> None:
    """Record the duration of a single Groq Whisper transcription call.

    Args:
        duration_seconds: Wall-clock time the call took.
    """
    VOICE_TRANSCRIPTION_LATENCY.observe(duration_seconds)


def record_node_duration(node_name: str, duration_seconds: float) -> None:
    """Record the execution duration of a single LangGraph node.

    Args:
        node_name: Name of the executed node.
        duration_seconds: Wall-clock time the node took to execute.
    """
    NODE_DURATION.labels(node_name=node_name).observe(duration_seconds)
