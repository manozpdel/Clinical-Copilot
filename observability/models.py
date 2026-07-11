"""Pydantic models for the observability layer.

This module is responsible ONLY for defining observability data
shapes. It contains no logging, tracing, metrics, or health-check
logic.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

HealthStatus = Literal["healthy", "degraded", "unhealthy", "disabled"]


class ComponentHealth(BaseModel):
    """The health status of a single application dependency.

    Attributes:
        name: Identifier of the checked component.
        status: The component's current health status.
        detail: Optional human-readable detail about the status.
        latency_ms: Optional time taken to perform the check.
    """

    name: str
    status: HealthStatus
    detail: str | None = None
    latency_ms: float | None = None


class HealthSummary(BaseModel):
    """The aggregated health of every checked application dependency.

    Attributes:
        status: The overall health status, worst of all components.
        components: Health of each individual checked component.
        checked_at: Timestamp the summary was generated.
    """

    status: HealthStatus
    components: list[ComponentHealth]
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NodeTiming(BaseModel):
    """A single LangGraph node's execution duration.

    Attributes:
        node_name: Name of the executed node.
        duration_seconds: Wall-clock time the node took to execute.
    """

    node_name: str
    duration_seconds: float
