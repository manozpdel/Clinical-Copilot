"""Evaluation configuration diagnostic endpoint.

This module is responsible ONLY for the `/api/evaluation` routes. It
contains no metric-calculation or judging logic; it reads existing
configuration via `EvaluationConfigService`.
"""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.services.evaluation_service import EvaluationConfigService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def get_evaluation_config_service(
    settings: Settings = Depends(get_settings),
) -> EvaluationConfigService:
    """Provide an EvaluationConfigService bound to the active settings.

    Args:
        settings: Active application settings.

    Returns:
        EvaluationConfigService: The configuration reporting service.
    """
    return EvaluationConfigService(settings)


@router.get("/config")
async def get_evaluation_config(
    service: EvaluationConfigService = Depends(get_evaluation_config_service),
) -> dict[str, object]:
    """Return the currently active evaluation configuration.

    Args:
        service: The evaluation config service, injected via dependency
            override in tests or the default settings-backed service in
            production.

    Returns:
        dict[str, object]: Whether evaluation is enabled, and the
            models configured for faithfulness and relevance judging.
    """
    return service.get_config()