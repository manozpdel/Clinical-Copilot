"""Tests for CSV/JSON feedback export."""

import csv
import io
import json

from feedback.export import export_to_csv, export_to_json


def _sample_rows() -> list[dict]:
    """Build a small set of representative export rows.

    Returns:
        list[dict]: Sample export rows.
    """
    return [
        {
            "feedback_id": "f1",
            "user_email": "alice@example.com",
            "conversation_id": "c1",
            "query_id": "q1",
            "is_helpful": True,
            "comment": "Great",
            "created_at": "2026-01-01T00:00:00",
        },
        {
            "feedback_id": "f2",
            "user_email": "bob@example.com",
            "conversation_id": "c2",
            "query_id": "q2",
            "is_helpful": False,
            "comment": "",
            "created_at": "2026-01-02T00:00:00",
        },
    ]


def test_export_to_csv_produces_valid_csv() -> None:
    """The CSV export should be parseable and contain all rows."""
    csv_text = export_to_csv(_sample_rows())

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["user_email"] == "alice@example.com"
    assert rows[1]["query_id"] == "q2"


def test_export_to_json_produces_valid_json() -> None:
    """The JSON export should be parseable and contain all rows."""
    json_text = export_to_json(_sample_rows())

    data = json.loads(json_text)

    assert len(data) == 2
    assert data[0]["feedback_id"] == "f1"
    assert data[1]["is_helpful"] is False


def test_export_to_csv_handles_empty_rows() -> None:
    """Exporting an empty row list should still produce a valid header-only CSV."""
    csv_text = export_to_csv([])

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    assert rows == []


def test_export_to_json_handles_empty_rows() -> None:
    """Exporting an empty row list should produce an empty JSON array."""
    json_text = export_to_json([])

    assert json.loads(json_text) == []
