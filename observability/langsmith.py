"""LangSmith tracing integration.

This module is responsible ONLY for configuring LangSmith environment
variables so that LangChain/LangGraph's built-in LangSmith tracing
picks them up automatically. It contains no metrics, logging, or
manual span-creation logic.
"""

import os

from app.core.config import Settings


def configure_langsmith(settings: Settings) -> bool:
    """Configure LangSmith tracing via environment variables.

    LangChain and LangGraph automatically send traces to LangSmith when
    `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT`
    are set in the environment; no explicit instrumentation calls are
    required elsewhere.

    Args:
        settings: Active application settings.

    Returns:
        bool: True if LangSmith tracing was enabled, False if it was
            left disabled (either explicitly, or because no API key was
            configured).
    """
    if not settings.enable_langsmith or not settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    return True


def is_langsmith_enabled(settings: Settings) -> bool:
    """Check whether LangSmith tracing is fully configured.

    Args:
        settings: Active application settings.

    Returns:
        bool: True if LangSmith is enabled and an API key is set.
    """
    return settings.enable_langsmith and bool(settings.langsmith_api_key)
