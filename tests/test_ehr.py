"""Tests for the mock EHR tool."""

import pytest

from tools.ehr import EHRTool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput
from tools.validator import ToolValidationError


def test_ehr_tool_returns_expected_fields_for_known_patient() -> None:
    """The EHR tool should return demographics, history, meds, allergies, labs."""
    tool = EHRTool()
    patient_id = next(iter(MOCK_PATIENTS.keys()))

    output = tool.execute(ToolInput(patient_id=patient_id))

    assert output.tool_name == "ehr"
    assert output.patient_id == patient_id
    assert "demographics" in output.data
    assert "medical_history" in output.data
    assert "medications" in output.data
    assert "allergies" in output.data
    assert "lab_summary" in output.data


def test_ehr_tool_raises_for_unknown_patient() -> None:
    """The EHR tool should raise a validation error for an unknown patient."""
    tool = EHRTool()

    with pytest.raises(ToolValidationError):
        tool.execute(ToolInput(patient_id="P9999"))