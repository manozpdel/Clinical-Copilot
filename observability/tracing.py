"""OpenTelemetry tracing configuration and utilities.

This module is responsible ONLY for initializing the OpenTelemetry
tracer provider, instrumenting FastAPI/SQLAlchemy, and providing a
reusable span context manager. It contains no logging, metrics, or
LangSmith logic.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import Settings

_SERVICE_NAME = "clinical-copilot-api"
_TRACER_NAME = "clinical-copilot"


def init_tracing(settings: Settings) -> trace.Tracer:
    """Initialize the global OpenTelemetry tracer provider.

    When tracing is disabled, the default (effectively no-op) global
    tracer provider is left in place. When enabled, spans are exported
    to the configured OTLP collector endpoint, or to the console if no
    endpoint is configured.

    Args:
        settings: Active application settings.

    Returns:
        trace.Tracer: The application's named tracer.
    """
    if settings.enable_tracing:
        resource = Resource.create({"service.name": _SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter = (
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            if settings.otel_exporter_otlp_endpoint
            else ConsoleSpanExporter()
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

    return trace.get_tracer(_TRACER_NAME)


def get_tracer() -> trace.Tracer:
    """Return the application's named tracer.

    Returns:
        trace.Tracer: A tracer bound to the currently configured
            global tracer provider.
    """
    return trace.get_tracer(_TRACER_NAME)


def instrument_fastapi(app: Any) -> None:
    """Instrument a FastAPI application for automatic HTTP request tracing.

    Args:
        app: The FastAPI application instance to instrument.
    """
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine: Any) -> None:
    """Instrument a SQLAlchemy async engine for automatic query tracing.

    Args:
        engine: The async SQLAlchemy engine to instrument. Its
            underlying synchronous engine is instrumented, since
            OpenTelemetry's SQLAlchemy instrumentation hooks into
            engine-level events.
    """
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


@contextmanager
def trace_span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    """Open a traced span for a block of code.

    Safe to use around both synchronous code and `await` expressions;
    when tracing is not initialized, this yields a no-op span.

    Args:
        name: Name of the span.
        **attributes: Span attributes to attach, with None values
            omitted.

    Yields:
        trace.Span: The active span.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
