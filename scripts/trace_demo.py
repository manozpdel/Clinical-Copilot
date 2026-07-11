"""CLI entry point that demonstrates the tracing utilities."""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from observability.tracing import init_tracing, trace_span


def main() -> None:
    """Initialize tracing and run a small nested-span demonstration."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    init_tracing(settings)

    with trace_span("demo.outer", demo="true"):
        logger.info("outer_span_started")
        with trace_span("demo.inner", step="1"):
            logger.info("inner_span_work")
        logger.info("outer_span_finished")

    print("Trace demo complete. Enable ENABLE_TRACING and set OTEL_EXPORTER_OTLP_ENDPOINT to export spans.")


if __name__ == "__main__":
    main()
