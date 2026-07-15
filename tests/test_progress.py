"""Tests for pipeline progress tracking."""

import pytest

from streaming.progress import ProgressTracker


def test_progress_starts_at_zero() -> None:
    """A freshly created tracker should report 0% before any stage advances."""
    tracker = ProgressTracker()

    assert tracker.percent() == 0.0


def test_progress_advances_through_stages() -> None:
    """Advancing through all stages should reach 100%."""
    tracker = ProgressTracker(stages=("a", "b", "c", "d"))

    assert tracker.advance("a") == 25.0
    assert tracker.advance("b") == 50.0
    assert tracker.advance("c") == 75.0
    assert tracker.advance("d") == 100.0


def test_progress_rejects_unknown_stage() -> None:
    """Advancing to an unconfigured stage name should raise ValueError."""
    tracker = ProgressTracker(stages=("a", "b"))

    with pytest.raises(ValueError):
        tracker.advance("unknown")
