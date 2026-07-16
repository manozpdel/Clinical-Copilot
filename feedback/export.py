"""CSV/JSON export of feedback data.

This module is responsible ONLY for serializing feedback records into
CSV or JSON text. It contains no persistence-write or analytics logic.
"""

import csv
import io
import json

from sqlalchemy.ext.asyncio import AsyncSession

from feedback.crud import list_all_feedback

_EXPORT_FIELDS: tuple[str, ...] = (
    "feedback_id",
    "user_email",
    "conversation_id",
    "query_id",
    "is_helpful",
    "comment",
    "created_at",
)


async def gather_export_rows(db: AsyncSession) -> list[dict]:
    """Build flat export rows from every feedback record.

    Args:
        db: Active async database session.

    Returns:
        list[dict]: One row per feedback record, containing the user's
            email, conversation ID, query ID, rating value, comment,
            and timestamp.
    """
    records = await list_all_feedback(db)

    rows: list[dict] = []
    for record in records:
        rows.append(
            {
                "feedback_id": str(record.id),
                "user_email": record.user.email if record.user else "",
                "conversation_id": (str(record.query.conversation_id) if record.query else ""),
                "query_id": str(record.query_id),
                "is_helpful": record.is_helpful,
                "comment": record.comment or "",
                "created_at": record.created_at.isoformat(),
            }
        )
    return rows


def export_to_csv(rows: list[dict]) -> str:
    """Serialize export rows into CSV text.

    Args:
        rows: The rows to serialize, each containing all keys in
            `_EXPORT_FIELDS`.

    Returns:
        str: The CSV document as text, including a header row.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_EXPORT_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def export_to_json(rows: list[dict]) -> str:
    """Serialize export rows into JSON text.

    Args:
        rows: The rows to serialize.

    Returns:
        str: The rows encoded as a JSON array, pretty-printed.
    """
    return json.dumps(rows, indent=2, default=str)
