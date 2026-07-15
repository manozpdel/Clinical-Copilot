"""Real-time streaming layer for Clinical Copilot.

This package provides SSE and WebSocket transports for streaming the
LangGraph agent's execution live: token-level generation, per-node
progress, tool execution, citations, and evaluation status. No
business logic from earlier milestones (retrieval, generation,
evaluation, tools) is duplicated here; existing pure functions are
reused and their intermediate results are emitted as events.
"""
