"""Rule-based tool routing for the mock clinical tools layer.

This module is responsible ONLY for selecting which tool (if any)
applies to a question, extracting the patient ID, and orchestrating
validated, retried execution through the registry. It contains no
tool implementation logic of its own.
"""

import re

from app.core.logging import get_logger
from tools.models import ToolExecutionResult, ToolInput, ToolName
from tools.registry import ToolRegistry
from tools.retry import RetryExhaustedError, retry_call
from tools.validator import ToolValidationError, validate_tool_input, validate_tool_output

logger = get_logger(__name__)

_PATIENT_ID_PATTERN = re.compile(r"\bP\d{3,4}\b", re.IGNORECASE)

_EHR_KEYWORDS: tuple[str, ...] = (
    "medication", "medications", "allergy", "allergies", "medical history",
    "demographic", "demographics", "lab", "labs",
)

_NOTES_KEYWORDS: tuple[str, ...] = (
    "note", "notes", "visit", "assessment", "physician", "chief complaint",
)

_WEARABLES_KEYWORDS: tuple[str, ...] = (
    "heart rate", "blood pressure", "sleep", "activity", "steps",
    "wearable", "wearables", "trend", "trends",
)


class ToolRouter:
    """Selects and executes a mock clinical tool for a user question."""

    def __init__(
        self,
        registry: ToolRegistry,
        known_patient_ids: set[str],
        max_retries: int = 3,
        retry_delay: float = 0.5,
        enable_validation: bool = True,
    ) -> None:
        """Initialize the tool router.

        Args:
            registry: Registry from which tools are looked up.
            known_patient_ids: The set of valid mock patient IDs.
            max_retries: Maximum number of execution attempts per tool
                call, including the first attempt.
            retry_delay: Delay, in seconds, between retry attempts.
            enable_validation: Whether tool input/output validation is
                enforced.
        """
        self._registry = registry
        self._known_patient_ids = known_patient_ids
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._enable_validation = enable_validation

    def extract_patient_id(self, question: str) -> str | None:
        """Extract a mock patient ID from a question, if present.

        Args:
            question: The user's natural language question.

        Returns:
            str | None: The normalized, uppercase patient ID (e.g.
                "P0005"), or None if no matching pattern is found.
        """
        match = _PATIENT_ID_PATTERN.search(question)
        return match.group(0).upper() if match else None

    def select_tool(self, question: str) -> str:
        """Select which tool applies to a question using keyword rules.

        Args:
            question: The user's natural language question.

        Returns:
            str: A `ToolName` value. Falls back to
                `ToolName.RETRIEVAL` when no patient ID is found or no
                keyword rule matches.
        """
        if self.extract_patient_id(question) is None:
            return ToolName.RETRIEVAL.value

        lowered = question.lower()

        if any(keyword in lowered for keyword in _EHR_KEYWORDS):
            return ToolName.EHR.value
        if any(keyword in lowered for keyword in _NOTES_KEYWORDS):
            return ToolName.NOTES.value
        if any(keyword in lowered for keyword in _WEARABLES_KEYWORDS):
            return ToolName.WEARABLES.value

        return ToolName.RETRIEVAL.value

    def route(self, question: str) -> ToolExecutionResult:
        """Select a tool for a question and execute it if one applies.

        Args:
            question: The user's natural language question.

        Returns:
            ToolExecutionResult: The routing and execution outcome. If
                no mock tool applies, `tool_name` is
                `ToolName.RETRIEVAL` and `output` is None, without
                treating this as an error.
        """
        tool_name = self.select_tool(question)
        patient_id = self.extract_patient_id(question)

        if tool_name == ToolName.RETRIEVAL.value:
            logger.info("tool_router_fallback_to_retrieval", question=question)
            return ToolExecutionResult(
                tool_name=tool_name, patient_id=patient_id, success=True
            )

        try:
            tool = self._registry.get_tool(tool_name)
            tool_input = ToolInput(patient_id=patient_id or "", query=question)

            if self._enable_validation:
                validate_tool_input(tool_input, self._known_patient_ids)

            output = retry_call(
                lambda: tool.execute(tool_input),
                max_attempts=self._max_retries,
                delay_seconds=self._retry_delay,
                retry_exceptions=(ConnectionError, TimeoutError),
            )

            if self._enable_validation:
                validate_tool_output(output)

            logger.info(
                "tool_router_execution_success",
                tool_name=tool_name,
                patient_id=patient_id,
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                patient_id=patient_id,
                success=True,
                output=output,
            )

        except (ToolValidationError, RetryExhaustedError) as error:
            logger.warning(
                "tool_router_execution_failed",
                tool_name=tool_name,
                patient_id=patient_id,
                error=str(error),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                patient_id=patient_id,
                success=False,
                error=str(error),
            )