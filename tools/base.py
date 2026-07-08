"""Abstract tool interface for the mock clinical tools layer.

This module is responsible ONLY for defining the contract every mock
clinical tool must implement. It contains no registration, routing,
validation, retry, or mock-data logic.
"""

from abc import ABC, abstractmethod

from tools.models import ToolInput, ToolOutput


class Tool(ABC):
    """Abstract base class for a mock clinical data tool."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool's unique identifier.

        Returns:
            str: The tool name, matching a `ToolName` value.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of the tool's purpose.

        Returns:
            str: The tool description.
        """
        raise NotImplementedError

    @property
    def input_schema(self) -> type[ToolInput]:
        """Return the Pydantic model describing this tool's input.

        Returns:
            type[ToolInput]: The input schema class.
        """
        return ToolInput

    @property
    def output_schema(self) -> type[ToolOutput]:
        """Return the Pydantic model describing this tool's output.

        Returns:
            type[ToolOutput]: The output schema class.
        """
        return ToolOutput

    @abstractmethod
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute the tool for a given input.

        Args:
            tool_input: The validated input parameters.

        Returns:
            ToolOutput: The tool's structured result.

        Raises:
            tools.validator.ToolValidationError: If the requested
                patient does not exist in the mock data population.
        """
        raise NotImplementedError