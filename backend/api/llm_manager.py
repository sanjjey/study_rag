import os
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from loguru import logger

from backend.prompts.templates import (
    RAG_PROMPT,
    HALLUCINATION_PROMPT,
    MOCK_TEST_PROMPT,
    EVALUATION_PROMPT,
)

_MAX_CONTEXT_CHARS = 12_000


def _trim_context(context: List[Dict[str, Any]]) -> str:
    """Serialise context chunks and trim to avoid exceeding token limits."""
    parts = []
    total = 0
    for i, chunk in enumerate(context):
        meta = chunk.get("metadata") or {}
        source = meta.get("book_name", "Unknown")
        page = meta.get("page_number", "")
        header = f"[Source {i+1}: {source}{', p.' + str(page) if page else ''}]"
        body = chunk.get("text", "")
        entry = f"{header}\n{body}"
        if total + len(entry) > _MAX_CONTEXT_CHARS:
            break
        parts.append(entry)
        total += len(entry)
    return "\n\n".join(parts)


class LLMManager:
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )
        logger.info(f"LLMManager ready (model={os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')})")

    def generate_rag_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        context_str = _trim_context(context)
        prompt = RAG_PROMPT.format(query=query, context=context_str)
        return self.llm.invoke(prompt).content

    def generate_hallucination_answer(self, query: str) -> str:
        prompt = HALLUCINATION_PROMPT.format(query=query)
        return self.llm.invoke(prompt).content

    def generate_mock_test(
        self,
        context: List[Dict[str, Any]],
        subject: str,
        difficulty: str,
        question_types: str,
        num_questions: int,
    ) -> str:
        context_str = _trim_context(context)
        prompt = MOCK_TEST_PROMPT.format(
            context=context_str,
            subject=subject,
            difficulty=difficulty,
            types=question_types,
            num_questions=num_questions,
        )
        return self.llm.invoke(prompt).content

    def evaluate_answer(self, query: str, student_answer: str, context: List[Dict[str, Any]]) -> str:
        context_str = _trim_context(context) if context else "No specific context available."
        prompt = EVALUATION_PROMPT.format(
            query=query,
            context=context_str,
            student_answer=student_answer,
        )
        return self.llm.invoke(prompt).content
