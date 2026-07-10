"""Tests for tool input/output validation utilities."""

import pytest

from tools.models import ToolInput, ToolOutput
from tools.validator import (
    ToolValidationError,
    validate_patient_exists,
    validate_patient_id_present,
    validate_tool_input,
    validate_tool_output,
)


def test_validate_patient_id_present_accepts_valid_id() -> None:
    """A non-empty patient ID should be returned unchanged (trimmed)."""
    assert validate_patient_id_present(" P0001 ") == "P0001"


def test_validate_patient_id_present_rejects_empty() -> None:
    """An empty or missing patient ID should raise an error."""
    with pytest.raises(ToolValidationError):
        validate_patient_id_present("")


def test_validate_patient_exists_accepts_known_id() -> None:
    """A known patient ID should not raise."""
    validate_patient_exists("P0001", {"P0001", "P0002"})


def test_validate_patient_exists_rejects_unknown_id() -> None:
    """An unknown patient ID should raise an error."""
    with pytest.raises(ToolValidationError):
        validate_patient_exists("P9999", {"P0001", "P0002"})


def test_validate_tool_input_checks_presence_and_existence() -> None:
    """Tool input validation should reject an unknown patient ID."""
    tool_input = ToolInput(patient_id="P9999")

    with pytest.raises(ToolValidationError):
        validate_tool_input(tool_input, {"P0001"})


def test_validate_tool_output_rejects_empty_data() -> None:
    """Tool output validation should reject an empty data payload."""
    output = ToolOutput(tool_name="ehr", patient_id="P0001", data={})

    with pytest.raises(ToolValidationError):
        validate_tool_output(output)


def test_validate_tool_output_accepts_populated_data() -> None:
    """Tool output validation should accept a non-empty data payload."""
    output = ToolOutput(tool_name="ehr", patient_id="P0001", data={"key": "value"})

    validate_tool_output(output)
