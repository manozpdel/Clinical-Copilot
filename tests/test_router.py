"""Tests for rule-based tool routing."""

from tools.ehr import EHRTool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolName
from tools.notes import NotesTool
from tools.registry import ToolRegistry
from tools.router import ToolRouter
from tools.wearables import WearablesTool


def _build_router() -> ToolRouter:
    """Build a fully wired tool router for use in tests.

    Returns:
        ToolRouter: A router with the EHR, Notes, and Wearables tools
            registered against the shared mock patient population.
    """
    registry = ToolRegistry()
    registry.register(EHRTool())
    registry.register(NotesTool())
    registry.register(WearablesTool())

    return ToolRouter(
        registry=registry,
        known_patient_ids=set(MOCK_PATIENTS.keys()),
        max_retries=2,
        retry_delay=0.0,
    )


def test_extract_patient_id_finds_valid_pattern() -> None:
    """A question containing a patient ID pattern should have it extracted."""
    router = _build_router()

    assert router.extract_patient_id("Show medications for patient P0005") == "P0005"


def test_extract_patient_id_returns_none_when_absent() -> None:
    """A question without a patient ID pattern should return None."""
    router = _build_router()

    assert router.extract_patient_id("What is diabetes?") is None


def test_select_tool_routes_medications_to_ehr() -> None:
    """A medications question with a patient ID should route to the EHR tool."""
    router = _build_router()

    assert router.select_tool("Show medications for patient P0005") == (
        ToolName.EHR.value
    )


def test_select_tool_routes_visit_to_notes() -> None:
    """A visit-notes question with a patient ID should route to the Notes tool."""
    router = _build_router()

    assert router.select_tool("What was the assessment at P0003's last visit?") == (
        ToolName.NOTES.value
    )


def test_select_tool_routes_heart_rate_to_wearables() -> None:
    """A heart-rate question with a patient ID should route to the Wearables tool."""
    router = _build_router()

    assert router.select_tool("What is the heart rate trend for P0002?") == (
        ToolName.WEARABLES.value
    )


def test_select_tool_falls_back_to_retrieval_without_patient_id() -> None:
    """A question without a patient ID should fall back to retrieval."""
    router = _build_router()

    assert router.select_tool("What medications treat hypertension?") == (
        ToolName.RETRIEVAL.value
    )


def test_route_executes_ehr_tool_successfully() -> None:
    """Routing a medications question should return the EHR tool's output."""
    router = _build_router()
    patient_id = next(iter(MOCK_PATIENTS.keys()))

    result = router.route(f"Show medications for patient {patient_id}")

    assert result.success is True
    assert result.tool_name == ToolName.EHR.value
    assert result.output is not None
    assert result.output.patient_id == patient_id


def test_route_returns_error_for_unknown_patient() -> None:
    """Routing with an unknown patient ID should return a failed result."""
    router = _build_router()

    result = router.route("Show medications for patient P9999")

    assert result.success is False
    assert result.error is not None


def test_route_falls_back_to_retrieval_cleanly() -> None:
    """Routing a non-tool question should return a successful retrieval fallback."""
    router = _build_router()

    result = router.route("What medications treat hypertension?")

    assert result.success is True
    assert result.tool_name == ToolName.RETRIEVAL.value
    assert result.output is None