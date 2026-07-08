"""LangGraph-powered agent layer for Clinical Copilot.

This package wraps the existing retrieval, generation, and evaluation
modules into a sequential LangGraph graph: Planner -> Retriever ->
Generator -> Evaluator. No new retrieval, generation, or evaluation
logic is implemented here; existing modules from the RAG and LLM
layers are reused and orchestrated.
"""