"""Groq communication for the Clinical Copilot RAG pipeline.

This module is responsible ONLY for communicating with the Groq chat
completion API, including client-side rate limiting, retry handling,
and (for streaming callers) incremental token generation. It contains
no prompt construction, retrieval, or citation logic. A single reusable
GroqClient can be instantiated multiple times with different API
keys/models to give each pipeline role its own independent quota. LLM
call latency is recorded via `observability.metrics` and traced via
`observability.tracing`, without altering the client's behavior.
"""

import random
import time
from collections.abc import Iterator

from groq import APIStatusError, RateLimitError
from langchain_groq import ChatGroq

from app.core.config import Settings
from app.core.logging import get_logger
from llm.rate_limiter import RateLimiter
from observability.metrics import record_llm_latency
from observability.tracing import trace_span

logger = get_logger(__name__)


def _extract_retry_after_seconds(error: APIStatusError) -> float | None:
    """Extract a server-provided retry delay from a rate limit error."""
    response = getattr(error, "response", None)
    if response is None:
        return None

    header_value = response.headers.get("retry-after")
    if header_value is None:
        return None

    try:
        return float(header_value)
    except ValueError:
        return None


class GroqClient:
    """A reusable wrapper around the ChatGroq chat completion API."""

    def __init__(self, settings: Settings, api_key: str, model: str) -> None:
        """Initialize the ChatGroq client with an explicit key and model.

        Args:
            settings: Application settings providing shared generation
                and rate-limiting parameters.
            api_key: The Groq API key this client instance should use.
            model: The Groq model name this client instance should use.
        """
        self._settings = settings
        self._model = model
        self._llm = ChatGroq(
            model=model,
            api_key=api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout=settings.llm_timeout,
            max_retries=0,
        )
        self._rate_limiter = RateLimiter(
            max_requests=settings.llm_requests_per_minute,
            period_seconds=60.0,
        )

    @property
    def model_name(self) -> str:
        """Return the model name this client instance uses."""
        return self._model

    def _compute_backoff_delay(self, attempt: int, retry_after: float | None) -> float:
        """Compute the delay to wait before the next retry attempt."""
        if retry_after is not None:
            base_delay = retry_after
        else:
            base_delay = self._settings.llm_retry_base_delay * (2**attempt)

        jitter = random.uniform(0, base_delay * 0.1)
        return min(base_delay + jitter, self._settings.llm_retry_max_delay)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a chat completion from a system and user prompt.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Returns:
            str: The model's generated text response.

        Raises:
            RateLimitError: If still rate limited after all retries.
        """
        max_attempts = self._settings.llm_max_retries + 1

        for attempt in range(max_attempts):
            self._rate_limiter.acquire()

            try:
                logger.info("llm_generation_started", model=self._model, attempt=attempt)
                call_start = time.monotonic()
                with trace_span("llm.generate", model=self._model, attempt=attempt):
                    response = self._llm.invoke([("system", system_prompt), ("human", user_prompt)])
                record_llm_latency(self._model, time.monotonic() - call_start)
                logger.info("llm_generation_completed", model=self._model)
                return str(response.content)

            except RateLimitError as error:
                if attempt == max_attempts - 1:
                    logger.error(
                        "llm_rate_limit_retries_exhausted",
                        model=self._model,
                        attempts=max_attempts,
                    )
                    raise

                retry_after = _extract_retry_after_seconds(error)
                delay = self._compute_backoff_delay(attempt, retry_after)
                logger.warning(
                    "llm_rate_limited_retrying",
                    model=self._model,
                    attempt=attempt,
                    delay_seconds=round(delay, 2),
                )
                time.sleep(delay)

        raise RuntimeError("Unreachable: retry loop exited without returning.")

    def generate_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """Generate a chat completion, yielding incremental text chunks.

        Unlike `generate`, this makes a single attempt with no
        rate-limit retry loop: a mid-stream failure cannot be cleanly
        resumed, so callers (see `streaming.service.StreamingService`)
        are expected to surface any raised exception as a stream
        `error` event rather than retrying transparently.

        Args:
            system_prompt: The system-level instructions for the model.
            user_prompt: The user-facing prompt content.

        Yields:
            str: Successive non-empty text chunks as they arrive.

        Raises:
            RateLimitError: If the request is rate limited.
        """
        self._rate_limiter.acquire()
        logger.info("llm_stream_started", model=self._model)
        call_start = time.monotonic()

        with trace_span("llm.generate_stream", model=self._model):
            for chunk in self._llm.stream([("system", system_prompt), ("human", user_prompt)]):
                piece = chunk.content
                if piece:
                    yield piece

        record_llm_latency(self._model, time.monotonic() - call_start)
        logger.info("llm_stream_completed", model=self._model)


def build_generation_client(settings: Settings) -> GroqClient:
    """Build the GroqClient used for answer generation."""
    return GroqClient(
        settings, api_key=settings.generation_api_key, model=settings.generation_model
    )


def build_faithfulness_client(settings: Settings) -> GroqClient:
    """Build the GroqClient used for faithfulness judging."""
    return GroqClient(
        settings,
        api_key=settings.faithfulness_api_key,
        model=settings.faithfulness_model,
    )


def build_relevance_client(settings: Settings) -> GroqClient:
    """Build the GroqClient used for answer relevance judging."""
    return GroqClient(settings, api_key=settings.relevance_api_key, model=settings.relevance_model)
