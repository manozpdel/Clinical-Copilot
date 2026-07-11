"""Text query endpoint.

This module is responsible ONLY for the `/api/query` route. Agent
execution is delegated to `QueryService`; rate limiting is delegated to
`security.limiter`; quota enforcement to `security.quota`; usage/cost
calculation to `security.budget`; and persistence to `database.crud`.
No business logic or raw SQL lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph
from app.core.config import Settings, get_settings
from app.schemas.requests import QueryRequest
from app.schemas.responses import QueryResponse
from app.services.query_service import QueryService
from auth.dependencies import get_current_user
from database.crud import create_usage_log, record_query_turn
from database.dependencies import get_db
from database.models import User
from security.budget import estimate_usage
from security.limiter import limiter, rate_limit_string
from security.quota import QuotaExceededError, check_quota_before_request

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
@limiter.limit(rate_limit_string)
async def submit_query(
    request: Request,
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    """Answer a text question using the existing LangGraph agent.

    Requires authentication, is rate-limited, and enforces per-user
    daily request / monthly token / monthly cost quotas before invoking
    the agent. The resulting conversation turn and usage are persisted
    under the authenticated user's account.

    Args:
        request: The incoming HTTP request, required by the rate
            limiter's key function.
        payload: The validated query request payload.
        current_user: The authenticated user, resolved from the bearer
            JWT.
        settings: Active application settings.
        db: Request-scoped async database session.
        service: The query service, injected via dependency override in
            tests or the default agent-backed service in production.

    Returns:
        QueryResponse: The generated answer, citations, evaluation,
            latency, and conversation/request identifiers.

    Raises:
        HTTPException: With status 429 if the user's quota has been
            exceeded.
    """
    try:
        await check_quota_before_request(db, current_user.id, settings)
    except QuotaExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)
        ) from error

    result = service.run_query(
        question=payload.question, conversation_id=payload.conversation_id
    )

    usage = estimate_usage(
        model=settings.generation_model,
        prompt_text=payload.question,
        completion_text=result["answer"],
    )

    conversation = await record_query_turn(
        db,
        user_id=current_user.id,
        conversation_id=result["conversation_id"],
        query_text=payload.question,
        response_text=result["answer"],
        citations=result["citations"],
        evaluation=result["evaluation"],
        latency_ms=result["latency_seconds"] * 1000,
    )

    await create_usage_log(
        db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        model=settings.generation_model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cost_usd=usage.cost_usd,
        latency_ms=result["latency_seconds"] * 1000,
    )

    return QueryResponse(**result)
