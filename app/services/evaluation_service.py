"""Business logic for evaluation-related REST endpoints.

This module is responsible ONLY for reading and shaping the current
evaluation configuration from application settings (Part 4). It
contains no FastAPI routing, metric calculation, or evaluation-pipeline
logic of its own.
"""

from typing import Any

from app.core.config import Settings


class EvaluationConfigService:
    """Reports the currently active evaluation configuration."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the evaluation config service.

        Args:
            settings: Active application settings.
        """
        self._settings = settings

    def get_config(self) -> dict[str, Any]:
        """Return the current evaluation configuration.

        Returns:
            dict[str, Any]: Whether evaluation is enabled, and the
                models configured for faithfulness and relevance
                judging.
        """
        return {
            "enable_evaluation": self._settings.enable_evaluation,
            "faithfulness_model": self._settings.faithfulness_model,
            "relevance_model": self._settings.relevance_model,
        }