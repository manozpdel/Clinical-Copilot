"""Tests for the mock Wearables tool."""

import pytest

from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput
from tools.validator import ToolValidationError
from tools.wearables import WearablesTool


def test_wearables_tool_returns_expected_fields_for_known_patient() -> None:
    """The Wearables tool should return vitals, sleep, activity, and trends."""
    tool = WearablesTool()
    patient_id = next(iter(MOCK_PATIENTS.keys()))

    output = tool.execute(ToolInput(patient_id=patient_id))

    assert output.tool_name == "wearables"
    assert output.patient_id == patient_id
    assert "heart_rate_bpm" in output.data
    assert "blood_pressure" in output.data
    assert "sleep_hours" in output.data
    assert "daily_steps" in output.data
    assert len(output.data["daily_trends"]) == 7


def test_wearables_tool_raises_for_unknown_patient() -> None:
    """The Wearables tool should raise a validation error for an unknown patient."""
    tool = WearablesTool()

    with pytest.raises(ToolValidationError):
        tool.execute(ToolInput(patient_id="P9999"))
