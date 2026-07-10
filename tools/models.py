"""Shared data models for the mock clinical tools layer.

This module is responsible ONLY for defining the data shapes used
across the tools package. It contains no tool implementation,
registration, routing, validation, or retry logic.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolName(StrEnum):
    """Identifiers for every routable option in the tools layer.

    Attributes:
        EHR: The mock electronic health record tool.
        NOTES: The mock clinical notes tool.
        WEARABLES: The mock wearables data tool.
        RETRIEVAL: Sentinel indicating no mock tool applies and the
            question should fall back to semantic retrieval.
    """

    EHR = "ehr"
    NOTES = "notes"
    WEARABLES = "wearables"
    RETRIEVAL = "retrieval"


class ToolInput(BaseModel):
    """Input parameters accepted by every mock clinical tool.

    Attributes:
        patient_id: Identifier of the patient to look up.
        query: The original user question, provided for tools that may
            use it for context.
    """

    patient_id: str
    query: str = ""


class ToolOutput(BaseModel):
    """Structured output returned by every mock clinical tool.

    Attributes:
        tool_name: Name of the tool that produced this output.
        patient_id: Identifier of the patient the data belongs to.
        data: The tool's structured result payload.
    """

    tool_name: str
    patient_id: str
    data: dict[str, Any]


class ToolExecutionResult(BaseModel):
    """The result of routing a question to a tool and executing it.

    Attributes:
        tool_name: Name of the tool that was selected, or
            `ToolName.RETRIEVAL` when no mock tool applied.
        patient_id: Identifier of the patient extracted from the
            question, if any.
        success: Whether tool execution completed without error.
        output: The tool's structured output, when execution succeeded
            and a mock tool was selected.
        error: A human-readable error message, when execution failed.
    """

    tool_name: str
    patient_id: str | None = None
    success: bool
    output: ToolOutput | None = None
    error: str | None = Field(default=None)
