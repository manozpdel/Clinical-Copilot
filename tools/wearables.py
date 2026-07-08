"""Mock Wearables tool.

This module is responsible ONLY for the Wearables tool's
implementation. It contains no registration, routing,
validation-utility, or retry logic of its own; it reuses
`tools.validator` for patient existence checks.
"""

from tools.base import Tool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput, ToolOutput
from tools.validator import validate_patient_exists, validate_patient_id_present


class WearablesTool(Tool):
    """Returns mock wearable device data: vitals, sleep, and activity."""

    @property
    def name(self) -> str:
        """Return this tool's unique identifier.

        Returns:
            str: "wearables".
        """
        return "wearables"

    @property
    def description(self) -> str:
        """Return a human-readable description of this tool.

        Returns:
            str: The tool description.
        """
        return (
            "Looks up a patient's wearable device data, including heart "
            "rate, blood pressure, sleep, daily activity, and recent "
            "daily trends."
        )

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Look up the wearable data for the requested patient.

        Args:
            tool_input: The validated input, containing the patient ID.

        Returns:
            ToolOutput: The patient's wearable device data.

        Raises:
            tools.validator.ToolValidationError: If the patient ID is
                missing or unknown.
        """
        patient_id = validate_patient_id_present(tool_input.patient_id)
        validate_patient_exists(patient_id, set(MOCK_PATIENTS.keys()))

        wearables = MOCK_PATIENTS[patient_id]["wearables"]

        return ToolOutput(
            tool_name=self.name,
            patient_id=patient_id,
            data=wearables,
        )