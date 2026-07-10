"""Tests for the tool registry."""

import pytest

from tools.ehr import EHRTool
from tools.registry import ToolNotFoundError, ToolRegistry


def test_register_and_get_tool() -> None:
    """A registered tool should be retrievable by its name."""
    registry = ToolRegistry()
    tool = EHRTool()

    registry.register(tool)

    assert registry.get_tool("ehr") is tool


def test_list_tools_returns_registered_names() -> None:
    """Listing tools should return every registered tool's name."""
    registry = ToolRegistry()
    registry.register(EHRTool())

    assert registry.list_tools() == ["ehr"]


def test_get_tool_raises_for_unknown_name() -> None:
    """Requesting an unregistered tool name should raise an error."""
    registry = ToolRegistry()

    with pytest.raises(ToolNotFoundError):
        registry.get_tool("unknown_tool")
