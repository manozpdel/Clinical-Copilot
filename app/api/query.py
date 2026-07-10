"""Text query endpoint.

This module is responsible ONLY for the `/api/query` route. Agent
execution is delegated to `QueryService`; persistence of the resulting
conversation turn is delegated to `database.crud.record_query_turn`.
No business logic or raw SQL lives here.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph
from app.core.config import Settings, get_settings
from app.schemas.requests import QueryRequest
from app.schemas.responses import QueryResponse
from app.services.query_service import QueryService
from auth.dependencies import get_current_user
from database.crud import record_query_turn
from database.dependencies import get_db
from database.models import User

router = APIRouter(prefix="/query", tags=["query"])

_query_service_singleton: QueryService | None = None


def get_query_service(settings: Settings = Depends(get_settings)) -> QueryService:
    """Provide a lazily-constructed, process-wide QueryService instance.

    Args:
        settings: Active application settings.

    Returns:
        QueryService: The shared query service instance, backed by the
            existing LangGraph agent graph.
    """
    global _query_service_singleton
    if _query_service_singleton is None:
        _query_service_singleton = QueryService(build_graph(settings))
    return _query_service_singleton


@router.post("", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """Answer a text question using the existing LangGraph agent.

    Requires authentication. The resulting conversation turn is
    persisted under the authenticated user's account.

    Args:
        request: The validated query request payload.
        current_user: The authenticated user, resolved from the bearer
            JWT.
        db: Request-scoped async database session.
        service: The query service, injected via dependency override in
            tests or the default agent-backed service in production.

    Returns:
        QueryResponse: The generated answer, citations, evaluation,
            latency, and conversation/request identifiers.
    """
    result = service.run_query(
        question=request.question, conversation_id=request.conversation_id
    )

    await record_query_turn(
        db,
        user_id=current_user.id,
        conversation_id=result["conversation_id"],
        query_text=request.question,
        response_text=result["answer"],
        citations=result["citations"],
        evaluation=result["evaluation"],
        latency_ms=result["latency_seconds"] * 1000,
    )

    return QueryResponse(**result)
