"""CLI entry point demonstrating mock clinical tool routing and execution."""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from tools.ehr import EHRTool
from tools.mock_data import MOCK_PATIENTS
from tools.models import ToolName
from tools.notes import NotesTool
from tools.registry import ToolRegistry
from tools.router import ToolRouter
from tools.wearables import WearablesTool


def _print_data(data: dict, indent: int = 0) -> None:
    """Recursively print a structured tool output payload.

    Args:
        data: The data payload to print.
        indent: Current indentation depth, in spaces.
    """
    prefix = " " * indent
    for key, value in data.items():
        label = key.replace("_", " ").title()
        if isinstance(value, dict):
            print(f"{prefix}{label}:")
            _print_data(value, indent + 2)
        elif isinstance(value, list):
            print(f"{prefix}{label}:")
            for item in value:
                if isinstance(item, dict):
                    _print_data(item, indent + 2)
                    print()
                else:
                    print(f"{prefix}  - {item}")
        else:
            print(f"{prefix}{label}: {value}")


def main() -> None:
    """Prompt for a question, route it to a tool, and print the output."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    registry = ToolRegistry()
    registry.register(EHRTool())
    registry.register(NotesTool())
    registry.register(WearablesTool())

    router = ToolRouter(
        registry=registry,
        known_patient_ids=set(MOCK_PATIENTS.keys()),
        max_retries=settings.max_tool_retries,
        retry_delay=settings.retry_delay,
        enable_validation=settings.enable_tool_validation,
    )

    print("Enter your question")
    question = input("> ").strip()

    if not question:
        print("No question entered. Exiting.")
        return

    result = router.route(question)

    print("\nTool Selected\n")
    if result.tool_name == ToolName.RETRIEVAL.value:
        print("None (falls back to semantic retrieval)")
    else:
        print(result.tool_name.upper())

    if not result.success:
        print(f"\nError: {result.error}")
        return

    if result.output is not None:
        print(f"\nPatient\n{result.patient_id}\n")
        print("Output\n")
        _print_data(result.output.data)

    logger.info(
        "tool_demo_finished", question=question, selected_tool=result.tool_name
    )


if __name__ == "__main__":
    main()