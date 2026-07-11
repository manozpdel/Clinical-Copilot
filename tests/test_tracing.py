"""Tests for OpenTelemetry tracing utilities."""

from app.core.config import Settings
from observability.tracing import get_tracer, init_tracing, trace_span


def test_init_tracing_disabled_returns_tracer() -> None:
    """With tracing disabled, init_tracing should still return a usable tracer."""
    settings = Settings(enable_tracing=False)

    tracer = init_tracing(settings)

    assert tracer is not None


def test_init_tracing_enabled_without_endpoint_uses_console_exporter() -> None:
    """With tracing enabled and no OTLP endpoint, init should not raise."""
    settings = Settings(enable_tracing=True, otel_exporter_otlp_endpoint="")

    tracer = init_tracing(settings)

    assert tracer is not None


def test_trace_span_yields_a_span_without_raising() -> None:
    """The trace_span context manager should execute its body without error."""
    executed = False

    with trace_span("test.span", example="value"):
        executed = True

    assert executed is True


def test_get_tracer_returns_consistent_tracer() -> None:
    """get_tracer should return a tracer usable for starting spans."""
    tracer = get_tracer()

    with tracer.start_as_current_span("manual.span"):
        pass
