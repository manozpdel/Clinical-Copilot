"""LLM-as-a-Judge utilities for scoring generated answers."""

import re

from llm.client import GroqClient

_SCORE_PATTERN = re.compile(r"([01](?:\.\d+)?)")

_JUDGE_SYSTEM_PROMPT = (
    "You are a precise, impartial evaluation judge that responds with a "
    "single numeric score and nothing else."
)

_FAITHFULNESS_TEMPLATE = (
    "You are an evaluation judge. Given the CONTEXT and the ANSWER "
    "below, score how faithful the ANSWER is to the CONTEXT on a scale "
    "from 0.0 to 1.0, where 1.0 means every claim in the ANSWER is fully "
    "supported by the CONTEXT and 0.0 means the ANSWER contains claims "
    "not supported by the CONTEXT at all. Respond with ONLY the numeric "
    "score.\n\n"
    "CONTEXT:\n{context}\n\n"
    "ANSWER:\n{answer}"
)

_RELEVANCE_TEMPLATE = (
    "You are an evaluation judge. Given the QUESTION and the ANSWER "
    "below, score how relevant the ANSWER is to the QUESTION on a scale "
    "from 0.0 to 1.0, where 1.0 means the ANSWER fully and directly "
    "addresses the QUESTION and 0.0 means the ANSWER is unrelated. "
    "Respond with ONLY the numeric score.\n\n"
    "QUESTION:\n{question}\n\n"
    "ANSWER:\n{answer}"
)


def _parse_score(raw_response: str) -> float:
    """Parse a numeric score in the range [0, 1] from a judge response.

    Args:
        raw_response: The raw text response from the judge model.

    Returns:
        float: The parsed score, clamped to [0.0, 1.0].
    """
    match = _SCORE_PATTERN.search(raw_response)
    if not match:
        return 0.0
    score = float(match.group(1))
    return max(0.0, min(1.0, score))


def score_faithfulness(context: str, answer: str, client: GroqClient) -> float:
    """Score how faithful an answer is to its supporting context.

    Args:
        context: The retrieved context the answer should be grounded in.
        answer: The model-generated answer text.
        client: GroqClient configured for the faithfulness judge role.

    Returns:
        float: A faithfulness score in the range [0.0, 1.0].
    """
    prompt = _FAITHFULNESS_TEMPLATE.format(context=context, answer=answer)
    raw_response = client.generate(system_prompt=_JUDGE_SYSTEM_PROMPT, user_prompt=prompt)
    return _parse_score(raw_response)


def score_answer_relevance(question: str, answer: str, client: GroqClient) -> float:
    """Score how relevant an answer is to its originating question.

    Args:
        question: The original user question.
        answer: The model-generated answer text.
        client: GroqClient configured for the relevance judge role.

    Returns:
        float: An answer relevance score in the range [0.0, 1.0].
    """
    prompt = _RELEVANCE_TEMPLATE.format(question=question, answer=answer)
    raw_response = client.generate(system_prompt=_JUDGE_SYSTEM_PROMPT, user_prompt=prompt)
    return _parse_score(raw_response)
