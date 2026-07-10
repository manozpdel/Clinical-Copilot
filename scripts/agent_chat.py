"""CLI entry point for chatting with the LangGraph-powered Clinical Copilot agent."""

from agent.graph import build_graph
from agent.state import create_empty_state
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def main() -> None:
    """Prompt for a question, run the agent graph, and print the results."""
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    print("Enter your question")
    question = input("> ").strip()

    if not question:
        print("No question entered. Exiting.")
        return

    graph = build_graph(settings)

    initial_state = create_empty_state()
    initial_state["question"] = question

    final_state = dict(initial_state)
    for step in graph.stream(initial_state):
        for node_name, node_update in step.items():
            final_state.update(node_update)
            print(f"{node_name.capitalize()} Complete")

    print("\nFinal Answer\n")
    print(final_state.get("answer", ""))

    print("\nCitations\n")
    for citation in final_state.get("citations", []):
        print(citation)

    print("\nEvaluation Scores\n")
    evaluation = final_state.get("evaluation", {})
    for key, value in evaluation.items():
        print(f"{key}: {value}")

    logger.info(
        "agent_chat_finished",
        request_id=final_state.get("request_id"),
        conversation_id=final_state.get("conversation_id"),
    )


if __name__ == "__main__":
    main()
