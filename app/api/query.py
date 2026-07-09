"""Text query endpoint.

This module is responsible ONLY for the `/api/query` route. It
contains no business logic; execution is delegated entirely to
`QueryService`.
"""

from fastapi import APIRouter, Depends

from agent.graph import build_graph
from app.core.config import Settings, get_settings
from app.schemas.requests import QueryRequest
from app.schemas.responses import QueryResponse
from app.services.query_service import QueryService

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
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """Answer a text question using the existing LangGraph agent.

    Args:
        request: The validated query request payload.
        service: The query service, injected via dependency override in
            tests or the default agent-backed service in production.

    Returns:
        QueryResponse: The generated answer, citations, evaluation,
            latency, and conversation/request identifiers.
    """
    result = service.run_query(
        question=request.question, conversation_id=request.conversation_id
    )
    return QueryResponse(**result)