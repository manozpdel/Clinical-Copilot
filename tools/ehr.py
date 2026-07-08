"""Mock Electronic Health Record (EHR) tool.

This module is responsible ONLY for the EHR tool's implementation. It
contains no registration, routing, validation-utility, or retry logic
of its own; it reuses `tools.validator` for patient existence checks.
"""

from tools.base import Tool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolInput, ToolOutput
from tools.validator import validate_patient_exists, validate_patient_id_present


class EHRTool(Tool):
    """Returns mock demographics, history, medications, allergies, and labs."""

    @property
    def name(self) -> str:
        """Return this tool's unique identifier.

        Returns:
            str: "ehr".
        """
        return "ehr"

    @property
    def description(self) -> str:
        """Return a human-readable description of this tool.

        Returns:
            str: The tool description.
        """
        return (
            "Looks up a patient's electronic health record, including "
            "demographics, medical history, current medications, "
            "allergies, and a lab summary."
        )

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Look up the EHR record for the requested patient.

        Args:
            tool_input: The validated input, containing the patient ID.

        Returns:
            ToolOutput: The patient's demographics, medical history,
                medications, allergies, and lab summary.

        Raises:
            tools.validator.ToolValidationError: If the patient ID is
                missing or unknown.
        """
        patient_id = validate_patient_id_present(tool_input.patient_id)
        validate_patient_exists(patient_id, set(MOCK_PATIENTS.keys()))

        record = MOCK_PATIENTS[patient_id]["ehr"]

        return ToolOutput(
            tool_name=self.name,
            patient_id=patient_id,
            data={
                "demographics": record["demographics"],
                "medical_history": record["medical_history"],
                "medications": record["medications"],
                "allergies": record["allergies"],
                "lab_summary": record["lab_summary"],
            },
        )