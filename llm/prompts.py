"""Prompt templates for the Clinical Copilot RAG pipeline.

This module is responsible ONLY for assembling prompts. It contains no
retrieval, generation, or citation-formatting logic.
"""

from dataclasses import dataclass

from rag.models import RetrievedChunk

SYSTEM_PROMPT = (
    "You are Clinical Copilot, a clinical information assistant. "
    "Answer the user's question using ONLY the retrieved context "
    "provided below. Never use outside knowledge and never hallucinate "
    "facts that are not present in the context. If the context does not "
    "contain enough information to answer the question, say so "
    "explicitly. "
    "Write your answer in plain, natural prose. Do NOT include inline "
    "citations, parenthetical source references, or phrases like "
    "'Patient ID:', 'Chunk ID:', or 'Source File:' within your answer "
    "text itself — a separate citations section listing this "
    "information is appended automatically after your response, so "
    "your job is only to write the answer, not the citations."
)


@dataclass(frozen=True)
class PromptBundle:
    """A fully assembled prompt ready to send to the language model.

    Attributes:
        system_prompt: The system-level instructions for the model.
        user_prompt: The user-facing prompt containing context and
            question.
    """

    system_prompt: str
    user_prompt: str


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Assemble retrieved chunks into a single context block.

    Args:
        chunks: Retrieved chunks to include as context.

    Returns:
        str: A formatted context block preserving each chunk's Patient
            ID, Chunk ID, Source File, and retrieved text. Returns a
            placeholder message when no chunks are provided.
    """
    if not chunks:
        return "No relevant context was retrieved."

    blocks = [
        f"Patient ID: {chunk.patient_id}\n"
        f"Chunk ID: {chunk.chunk_id}\n"
        f"Source File: {chunk.source_file}\n"
        f"Text: {chunk.text}"
        for chunk in chunks
    ]
    return "\n\n".join(blocks)


def build_user_prompt(question: str, context: str) -> str:
    """Assemble the user-facing prompt from context and a question.

    Args:
        question: The user's natural language question.
        context: The formatted retrieved context block.

    Returns:
        str: The complete user prompt to send to the language model.
    """
    return (
        "Retrieved Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Instructions:\n"
        "- Answer using only the retrieved context above.\n"
        "- Never hallucinate information not present in the context.\n"
        "- Write plain prose only. Do not include Patient ID, Chunk ID, "
        "or Source File references inline in your answer — citations "
        "are handled separately."
    )


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> PromptBundle:
    """Build the complete system and user prompt for a RAG query.

    Args:
        question: The user's natural language question.
        chunks: Retrieved chunks to use as context.

    Returns:
        PromptBundle: The assembled system and user prompts.
    """
    context = build_context(chunks)
    user_prompt = build_user_prompt(question, context)
    return PromptBundle(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)