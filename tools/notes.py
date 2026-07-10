"""Mock Clinical Notes tool.

This module is responsible ONLY for the Clinical Notes tool's
implementation. It contains no registration, routing,
validation-utility, or retry logic of its own; it reuses
`tools.validator` for patient existence checks.
"""

from tools.base import Tool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput, ToolOutput
from tools.validator import validate_patient_exists, validate_patient_id_present


class NotesTool(Tool):
    """Returns mock physician visit notes, assessments, and plans."""

    @property
    def name(self) -> str:
        """Return this tool's unique identifier.

        Returns:
            str: "notes".
        """
        return "notes"

    @property
    def description(self) -> str:
        """Return a human-readable description of this tool.

        Returns:
            str: The tool description.
        """
        return (
            "Looks up a patient's physician visit notes, including "
            "visit dates, chief complaints, assessments, and plans."
        )

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Look up the clinical notes for the requested patient.

        Args:
            tool_input: The validated input, containing the patient ID.

        Returns:
            ToolOutput: The patient's visit notes.

        Raises:
            tools.validator.ToolValidationError: If the patient ID is
                missing or unknown.
        """
        patient_id = validate_patient_id_present(tool_input.patient_id)
        validate_patient_exists(patient_id, set(MOCK_PATIENTS.keys()))

        notes = MOCK_PATIENTS[patient_id]["notes"]

        return ToolOutput(
            tool_name=self.name,
            patient_id=patient_id,
            data={"visit_notes": notes},
        )
