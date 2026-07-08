"""Answer generation logic for the Clinical Copilot agent.

This module is responsible ONLY for building the prompt, invoking the
existing ChatGroq wrapper (Part 4), and formatting citations. It
contains no retrieval or evaluation logic, and reuses
`llm.prompts.build_prompt`, `llm.client.GroqClient`, and
`llm.citation` rather than reimplementing them.
"""

from llm.citation import append_citations, extract_citations
from llm.client import GroqClient
from llm.prompts import PromptBundle, build_prompt
from rag.models import RetrievedChunk


def generate_response(
    question: str,
    chunks: list[RetrievedChunk],
    client: GroqClient,
) -> tuple[str, list[str], PromptBundle]:
    """Build the prompt and generate an answer with citations.

    Args:
        question: The normalized user question.
        chunks: The retrieved chunks to use as context.
        client: GroqClient used to generate the raw answer.

    Returns:
        tuple[str, list[str], PromptBundle]: The final answer (with
            citations appended), the extracted citation strings, and
            the prompt bundle used to generate the answer.
    """
    prompt = build_prompt(question=question, chunks=chunks)
    raw_answer = client.generate(
        system_prompt=prompt.system_prompt, user_prompt=prompt.user_prompt
    )

    citations = extract_citations(chunks)
    final_answer = append_citations(raw_answer, chunks)

    return final_answer, citations, prompt