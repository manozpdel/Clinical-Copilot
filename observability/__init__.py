"""Production observability layer for Clinical Copilot.

This package provides structured logging context helpers, request/
correlation ID generation, OpenTelemetry tracing, Prometheus metrics,
LangSmith integration, observability middleware, health checks, and
dashboard helper utilities. No business logic from earlier milestones
is duplicated here; existing modules are only instrumented.
"""
