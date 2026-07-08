"""Tests for the mock Clinical Notes tool."""

import pytest

from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput
from tools.notes import NotesTool
from tools.validator import ToolValidationError


def test_notes_tool_returns_visit_notes_for_known_patient() -> None:
    """The Notes tool should return at least one visit note."""
    tool = NotesTool()
    patient_id = next(iter(MOCK_PATIENTS.keys()))

    output = tool.execute(ToolInput(patient_id=patient_id))

    assert output.tool_name == "notes"
    assert output.patient_id == patient_id
    assert "visit_notes" in output.data
    assert len(output.data["visit_notes"]) >= 1
    assert "assessment" in output.data["visit_notes"][0]
    assert "plan" in output.data["visit_notes"][0]


def test_notes_tool_raises_for_unknown_patient() -> None:
    """The Notes tool should raise a validation error for an unknown patient."""
    tool = NotesTool()

    with pytest.raises(ToolValidationError):
        tool.execute(ToolInput(patient_id="P9999"))