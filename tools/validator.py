"""Validation utilities for the mock clinical tools layer.

This module is responsible ONLY for validating tool inputs and
outputs. It contains no tool implementation, registration, routing, or
retry logic.
"""

from tools.models import ToolInput, ToolOutput


class ToolValidationError(Exception):
    """Raised when tool input or output fails validation."""


def validate_patient_id_present(patient_id: str | None) -> str:
    """Validate that a patient ID was supplied and is non-empty.

    Args:
        patient_id: The candidate patient ID, possibly None or blank.

    Returns:
        str: The validated, non-empty patient ID.

    Raises:
        ToolValidationError: If `patient_id` is None or blank.
    """
    if not patient_id or not patient_id.strip():
        raise ToolValidationError("A patient_id is required but was not provided.")
    return patient_id.strip()


def validate_patient_exists(patient_id: str, known_patient_ids: set[str]) -> None:
    """Validate that a patient ID exists in the known patient population.

    Args:
        patient_id: The patient ID to check.
        known_patient_ids: The set of valid patient IDs.

    Raises:
        ToolValidationError: If `patient_id` is not in
            `known_patient_ids`.
    """
    if patient_id not in known_patient_ids:
        raise ToolValidationError(f"Unknown patient_id: '{patient_id}'.")


def validate_tool_input(tool_input: ToolInput, known_patient_ids: set[str]) -> None:
    """Validate a tool input's patient ID presence and existence.

    Args:
        tool_input: The tool input to validate.
        known_patient_ids: The set of valid patient IDs.

    Raises:
        ToolValidationError: If the patient ID is missing or unknown.
    """
    patient_id = validate_patient_id_present(tool_input.patient_id)
    validate_patient_exists(patient_id, known_patient_ids)


def validate_tool_output(output: ToolOutput) -> None:
    """Validate that a tool output carries a non-empty data payload.

    Args:
        output: The tool output to validate.

    Raises:
        ToolValidationError: If `output.data` is empty.
    """
    if not output.data:
        raise ToolValidationError(
            f"Tool '{output.tool_name}' returned an empty data payload "
            f"for patient '{output.patient_id}'."
        )