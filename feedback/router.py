"""FastAPI routes for the human feedback system.

This module is responsible ONLY for the `/feedback/*` routes. All
business logic is delegated to `FeedbackService`, `feedback.analytics`,
`feedback.comparison`, and `feedback.export`. No persistence or
validation logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi import Query as QueryParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from auth.dependencies import get_current_user
from database.dependencies import get_db
from database.models import User
from feedback.analytics import compute_analytics
from feedback.comparison import ComparisonError, compare_queries
from feedback.crud import (
    get_feedback_by_user_and_query,
    get_history_for_user,
    get_rating_by_user_and_query,
)
from feedback.dependencies import get_feedback_service, require_admin
from feedback.export import export_to_csv, export_to_json, gather_export_rows
from feedback.schemas import (
    AnalyticsResponse,
    ComparisonResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
    FeedbackUpdateRequest,
    HallucinationReportRequest,
    HallucinationReportResponse,
    HistoryItem,
    RatingCreateRequest,
    RatingResponse,
)
from feedback.service import (
    FeedbackNotFoundError,
    FeedbackPermissionError,
    FeedbackService,
    FeedbackValidationError,
    QueryNotFoundError,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _to_feedback_response(feedback) -> FeedbackResponse:
    """Convert an ORM Feedback record into its response schema.

    Args:
        feedback: The ORM Feedback instance.

    Returns:
        FeedbackResponse: The converted schema.
    """
    return FeedbackResponse(
        id=str(feedback.id),
        query_id=str(feedback.query_id),
        is_helpful=feedback.is_helpful,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


def _to_rating_response(rating) -> RatingResponse:
    """Convert an ORM Rating record into its response schema.

    Args:
        rating: The ORM Rating instance.

    Returns:
        RatingResponse: The converted schema.
    """
    return RatingResponse(
        id=str(rating.id),
        query_id=str(rating.query_id),
        stars=rating.stars,
        created_at=rating.created_at,
        updated_at=rating.updated_at,
    )


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    settings: Settings = Depends(get_settings),
) -> FeedbackResponse:
    """Submit (or update) thumbs-up/down and comment feedback on a response.

    Args:
        request: The validated feedback submission.
        current_user: The authenticated user.
        service: The feedback service.
        settings: Active application settings.

    Returns:
        FeedbackResponse: The created or updated feedback record.

    Raises:
        HTTPException: With status 404 if the feedback system is
            disabled or the referenced query is not found/owned, or
            400 if the comment is too long.
    """
    if not settings.enable_feedback:
        raise HTTPException(status_code=404, detail="Feedback is disabled.")

    try:
        feedback = await service.submit_feedback(
            current_user.id, request.query_id, request.is_helpful, request.comment
        )
    except QueryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _to_feedback_response(feedback)


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    request: FeedbackUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackResponse:
    """Update an existing feedback record owned by the current user.

    Args:
        feedback_id: Identifier of the feedback record to update.
        request: The updated feedback content.
        current_user: The authenticated user.
        service: The feedback service.

    Returns:
        FeedbackResponse: The updated feedback record.

    Raises:
        HTTPException: With status 404 if not found, 403 if not owned,
            or 400 if the comment is too long.
    """
    try:
        feedback = await service.update_feedback(
            current_user.id, feedback_id, request.is_helpful, request.comment
        )
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackPermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except FeedbackValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _to_feedback_response(feedback)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
) -> None:
    """Delete a feedback record owned by the current user.

    Args:
        feedback_id: Identifier of the feedback record to delete.
        current_user: The authenticated user.
        service: The feedback service.

    Raises:
        HTTPException: With status 404 if not found, or 403 if not
            owned.
    """
    try:
        await service.delete_feedback(current_user.id, feedback_id)
    except FeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackPermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/rating", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def submit_rating(
    request: RatingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
) -> RatingResponse:
    """Submit (or update) a 1-5 star rating for a response.

    Args:
        request: The validated rating submission.
        current_user: The authenticated user.
        service: The feedback service.

    Returns:
        RatingResponse: The created or updated rating record.

    Raises:
        HTTPException: With status 404 if the query is not found/owned,
            or 400 if the rating value is invalid.
    """
    try:
        rating = await service.submit_rating(current_user.id, request.query_id, request.stars)
    except QueryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _to_rating_response(rating)


@router.post(
    "/report",
    response_model=HallucinationReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_hallucination_report(
    request: HallucinationReportRequest,
    current_user: User = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
    settings: Settings = Depends(get_settings),
) -> HallucinationReportResponse:
    """Report a hallucination, citation, safety, or completeness issue.

    Args:
        request: The validated report submission.
        current_user: The authenticated user.
        service: The feedback service.
        settings: Active application settings.

    Returns:
        HallucinationReportResponse: The newly created report.

    Raises:
        HTTPException: With status 404 if hallucination reports are
            disabled or the query is not found/owned, or 400 if the
            detail text is too long.
    """
    if not settings.enable_hallucination_reports:
        raise HTTPException(status_code=404, detail="Hallucination reports are disabled.")

    try:
        report = await service.submit_hallucination_report(
            current_user.id, request.query_id, request.reason, request.detail
        )
    except QueryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return HallucinationReportResponse(
        id=str(report.id),
        query_id=str(report.query_id),
        reason=report.reason,
        detail=report.detail,
        created_at=report.created_at,
    )


@router.get("/history", response_model=list[HistoryItem])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = QueryParam(default=50, ge=1, le=200),
) -> list[HistoryItem]:
    """List the current user's own conversation history with feedback attached.

    Args:
        current_user: The authenticated user.
        db: Request-scoped async database session.
        limit: Maximum number of queries to return.

    Returns:
        list[HistoryItem]: The user's queries, most recent first, each
            with its citations, evaluation, feedback, and rating.
    """
    queries = await get_history_for_user(db, current_user.id, limit)

    items: list[HistoryItem] = []
    for query in queries:
        feedback = await get_feedback_by_user_and_query(db, current_user.id, query.id)
        rating = await get_rating_by_user_and_query(db, current_user.id, query.id)
        items.append(
            HistoryItem(
                query_id=str(query.id),
                conversation_id=str(query.conversation_id),
                query_text=query.query_text,
                response_text=query.response_text,
                citations=query.citations,
                evaluation=query.evaluation,
                created_at=query.created_at,
                feedback=_to_feedback_response(feedback) if feedback else None,
                rating=_to_rating_response(rating) if rating else None,
            )
        )
    return items


@router.get("/compare", response_model=ComparisonResponse)
async def compare_responses(
    query_id_a: str,
    query_id_b: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Compare two of the current user's own responses side by side.

    Args:
        query_id_a: Identifier of the first query.
        query_id_b: Identifier of the second query.
        current_user: The authenticated user.
        db: Request-scoped async database session.

    Returns:
        ComparisonResponse: Both responses with citations, evaluation,
            feedback, and ratings.

    Raises:
        HTTPException: With status 404 if either query is not
            found/owned.
    """
    try:
        return await compare_queries(db, current_user.id, query_id_a, query_id_b)
    except ComparisonError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AnalyticsResponse:
    """Return aggregated feedback analytics. Requires administrator access.

    Args:
        db: Request-scoped async database session.
        _admin: The authenticated administrator (enforced by
            dependency, unused directly).

    Returns:
        AnalyticsResponse: Average rating, positive/negative
            percentages, hallucination report breakdown, most common
            issues, and a 30-day daily trend.
    """
    return await compute_analytics(db)


@router.get("/export")
async def export_feedback(
    export_format: str = QueryParam(default="json", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> Response:
    """Export all feedback records as CSV or JSON. Requires administrator access.

    Args:
        export_format: The export format, either "csv" or "json".
        db: Request-scoped async database session.
        settings: Active application settings.
        _admin: The authenticated administrator (enforced by
            dependency, unused directly).

    Returns:
        Response: The exported feedback data, with an appropriate
            media type and download filename.

    Raises:
        HTTPException: With status 404 if export is disabled.
    """
    if not settings.enable_export:
        raise HTTPException(status_code=404, detail="Feedback export is disabled.")

    rows = await gather_export_rows(db)

    if export_format == "csv":
        content = export_to_csv(rows)
        media_type = "text/csv"
        filename = "feedback_export.csv"
    else:
        content = export_to_json(rows)
        media_type = "application/json"
        filename = "feedback_export.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
