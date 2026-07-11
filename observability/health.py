"""Application dependency health checks.

This module is responsible ONLY for checking the status of the
database, ChromaDB, Groq, LangSmith, disk, and memory, and composing
them into a summary. It contains no logging, tracing, or metrics logic.
"""

import resource
import shutil
import time

from sqlalchemy import text

from app.core.config import Settings
from observability.langsmith import is_langsmith_enabled
from observability.models import ComponentHealth, HealthSummary
from rag.retriever import ChromaRetriever


class HealthService:
    """Checks the health of every external dependency the app relies on."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the health service.

        Args:
            settings: Active application settings.
        """
        self._settings = settings
        from sqlalchemy.ext.asyncio import create_async_engine
        self._engine = create_async_engine(
            settings.database_url,
            connect_args={"connect_timeout": 5},
            pool_size=1,
            max_overflow=0,
        )

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity by running a trivial query.

        Returns:
            ComponentHealth: "healthy" if the query succeeds, otherwise
                "unhealthy" with the error detail.
        """
        start = time.monotonic()
        try:
            # Force a new connection rather than using a cached one
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            return ComponentHealth(
                name="database",
                status="healthy",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as error:  # noqa: BLE001
            return ComponentHealth(
                name="database",
                status="unhealthy",
                detail=str(error),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def check_chroma(self) -> ComponentHealth:
        """Check ChromaDB connectivity by loading the collection and counting it.

        Returns:
            ComponentHealth: "healthy" if the collection is reachable,
                otherwise "unhealthy" with the error detail.
        """
        start = time.monotonic()
        try:
            retriever = ChromaRetriever(self._settings)
            count = retriever.count()
            return ComponentHealth(
                name="chromadb",
                status="healthy",
                detail=f"{count} chunks in collection.",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as error:  # noqa: BLE001
            return ComponentHealth(
                name="chromadb",
                status="unhealthy",
                detail=str(error),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def check_groq(self) -> ComponentHealth:
        """Check that a Groq API key is configured.

        This is a configuration check, not a live network call, to
        keep health checks fast and independent of Groq availability.

        Returns:
            ComponentHealth: "healthy" if an API key is configured,
                otherwise "unhealthy".
        """
        if self._settings.generation_api_key:
            return ComponentHealth(name="groq", status="healthy")
        return ComponentHealth(
            name="groq", status="unhealthy", detail="No Groq API key configured."
        )

    def check_langsmith(self) -> ComponentHealth:
        """Check LangSmith configuration status.

        Returns:
            ComponentHealth: "disabled" if LangSmith is turned off,
                "unhealthy" if enabled without an API key, otherwise
                "healthy".
        """
        if not self._settings.enable_langsmith:
            return ComponentHealth(name="langsmith", status="disabled")
        if not is_langsmith_enabled(self._settings):
            return ComponentHealth(
                name="langsmith", status="unhealthy", detail="No API key configured."
            )
        return ComponentHealth(name="langsmith", status="healthy")

    def check_disk(self) -> ComponentHealth:
        """Check available disk space on the current filesystem.

        Returns:
            ComponentHealth: "healthy" if at least 10% free space
                remains, otherwise "degraded".
        """
        usage = shutil.disk_usage(".")
        percent_free = (usage.free / usage.total) * 100
        status = "healthy" if percent_free >= 10.0 else "degraded"
        return ComponentHealth(
            name="disk", status=status, detail=f"{percent_free:.1f}% free."
        )

    def check_memory(self) -> ComponentHealth:
        """Report the process's approximate peak memory usage.

        Returns:
            ComponentHealth: Always "healthy"; reported for visibility
                rather than threshold enforcement.
        """
        max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return ComponentHealth(
            name="memory", status="healthy", detail=f"peak RSS ~{max_rss_kb} KB."
        )

    async def get_summary(self) -> HealthSummary:
        """Run every health check and compose an overall summary.

        Returns:
            HealthSummary: The aggregated health of all components,
                with overall status "unhealthy" if any component is
                unhealthy, "degraded" if any is degraded, otherwise
                "healthy".
        """
        components = [
            await self.check_database(),
            self.check_chroma(),
            self.check_groq(),
            self.check_langsmith(),
            self.check_disk(),
            self.check_memory(),
        ]

        statuses = {component.status for component in components}
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthSummary(status=overall, components=components)
