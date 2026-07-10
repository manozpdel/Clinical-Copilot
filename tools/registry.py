"""Tool registration for the mock clinical tools layer.

This module is responsible ONLY for registering and looking up tool
instances. It contains no tool implementation, routing, validation, or
retry logic. Callers must never instantiate tools directly; they
should always go through a `ToolRegistry`.
"""

from tools.base import Tool


class ToolNotFoundError(Exception):
    """Raised when a requested tool name is not registered."""


class ToolRegistry:
    """A registry of available mock clinical tools, keyed by name."""

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance under its own name.

        Args:
            tool: The tool instance to register.
        """
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Retrieve a registered tool by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            Tool: The registered tool instance.

        Raises:
            ToolNotFoundError: If no tool is registered under `name`.
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"No tool registered with name '{name}'.")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """List the names of all registered tools.

        Returns:
            list[str]: Registered tool names, in registration order.
        """
        return list(self._tools.keys())
