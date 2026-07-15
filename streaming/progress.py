"""Pipeline progress tracking.

This module is responsible ONLY for computing overall completion
percentage across the pipeline's ordered stages. It contains no event
construction or transport logic.
"""

STAGES: tuple[str, ...] = ("planner", "context", "generator", "evaluator")


class ProgressTracker:
    """Tracks which pipeline stage is active and the resulting completion percent."""

    def __init__(self, stages: tuple[str, ...] = STAGES) -> None:
        """Initialize the tracker.

        Args:
            stages: The ordered stage names comprising a full pipeline
                run.
        """
        self._stages = stages
        self._current_index = -1

    def advance(self, stage: str) -> float:
        """Mark a stage as active and return the resulting completion percent.

        Args:
            stage: Name of the stage now active. Must be one of the
                configured `stages`.

        Returns:
            float: Completion percent in [0, 100], based on the
                1-indexed position of `stage` among all stages.

        Raises:
            ValueError: If `stage` is not a configured stage name.
        """
        if stage not in self._stages:
            raise ValueError(f"Unknown stage: '{stage}'.")

        self._current_index = self._stages.index(stage)
        return self.percent()

    def percent(self) -> float:
        """Return the completion percent for the currently active stage.

        Returns:
            float: 0.0 if no stage has been advanced to yet, otherwise
                the percent complete based on stage position.
        """
        if self._current_index < 0:
            return 0.0
        return round(((self._current_index + 1) / len(self._stages)) * 100, 2)
