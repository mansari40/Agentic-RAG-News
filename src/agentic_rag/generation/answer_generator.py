"""
Answer Generator — LangChain ChatOpenAI for answer synthesis.

Selects an adaptive response format based on the query type and evidence
confidence before generating, so the LLM never has to produce sections
that the retrieved sources don't support.
"""

from datetime import datetime
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.prompts.prompts_template import (
    SYNTHESIS_FORMAT_ANALYTICAL,
    SYNTHESIS_FORMAT_LOW_CONFIDENCE,
    SYNTHESIS_FORMAT_SIMPLE,
    SYNTHESIS_FORMAT_TEMPORAL,
    SYNTHESIS_SYSTEM_PROMPT_BASE,
    SYNTHESIS_USER_PROMPT,
    format_key_facts,
    format_verified_sources_for_synthesis,
)
from agentic_rag.utils import extract_token_cost
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)

# Confidence threshold below which we switch to the limited-evidence format
_LOW_CONFIDENCE_THRESHOLD = 0.50


class AgenticAnswerGenerator:
    """Generates analyst-style answers from LLM-verified sources."""

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=agentic_settings.chat_model_name,
            temperature=agentic_settings.synthesis_temperature,
            max_tokens=agentic_settings.max_synthesis_tokens,
        )
        self.last_call_cost: float = 0.0
        self.last_call_tokens: int = 0

    def generate(
        self,
        query: str,
        sources: list[dict[str, Any]],
        key_facts: list[str] | None = None,
        max_tokens: int | None = None,
        query_type: str = "simple",
        confidence_score: float = 1.0,
    ) -> str:
        self.last_call_cost = 0.0
        self.last_call_tokens = 0

        if not sources:
            return "I couldn't find relevant German timber market information for your question."

        today = datetime.now().strftime("%Y-%m-%d")
        context = format_verified_sources_for_synthesis(
            sources[: agentic_settings.max_sources_to_synthesize],
            max_chars=agentic_settings.max_content_chars_per_source,
        )
        key_facts_section = format_key_facts(key_facts or [])

        # Pick the format that matches the query intent and evidence strength
        format_instructions = self._select_format(query_type, confidence_score)
        system_prompt = SYNTHESIS_SYSTEM_PROMPT_BASE.format(format_instructions=format_instructions)

        user_prompt = SYNTHESIS_USER_PROMPT.format(
            query=query,
            today=today,
            context=context,
            key_facts_section=key_facts_section,
        )

        # Use a fresh LLM if caller requests a different token limit
        llm = self._llm
        if max_tokens and max_tokens != agentic_settings.max_synthesis_tokens:
            llm = ChatOpenAI(
                model=agentic_settings.chat_model_name,
                temperature=agentic_settings.synthesis_temperature,
                max_tokens=max_tokens,
            )

        try:
            response = llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            t_in, t_out, cost = extract_token_cost(
                response,
                agentic_settings.openai_input_cost_per_token,
                agentic_settings.openai_output_cost_per_token,
            )
            self.last_call_tokens = t_in + t_out
            self.last_call_cost = cost

            answer = (response.content or "").strip()
            fmt = self._format_name(query_type, confidence_score)
            logger.info(
                f"Generator: {len(answer)} chars | format={fmt} | "
                f"{self.last_call_tokens} tokens | ${self.last_call_cost:.6f}"
            )
            return answer

        except Exception as exc:
            logger.error(f"Generation error: {exc}")
            return self._fallback_answer(sources)

    # Private helpers

    def _select_format(self, query_type: str, confidence_score: float) -> str:
        """
        Return the right format instructions for this query.

        Low confidence always wins — if evidence is thin, use the
        limited-evidence format regardless of query type.
        For normal confidence, pick by query intent.
        """
        if confidence_score < _LOW_CONFIDENCE_THRESHOLD:
            return str(SYNTHESIS_FORMAT_LOW_CONFIDENCE)

        if query_type in ("comparison", "multi_hop"):
            return str(SYNTHESIS_FORMAT_ANALYTICAL)

        if query_type == "temporal":
            return str(SYNTHESIS_FORMAT_TEMPORAL)

        # "simple" and any unrecognised type → direct factual format
        return str(SYNTHESIS_FORMAT_SIMPLE)

    def _format_name(self, query_type: str, confidence_score: float) -> str:
        """Return a short label for logging which format was selected."""
        if confidence_score < _LOW_CONFIDENCE_THRESHOLD:
            return "low_confidence"
        if query_type in ("comparison", "multi_hop"):
            return "analytical"
        if query_type == "temporal":
            return "temporal"
        return "simple"

    def _fallback_answer(self, sources: list[dict[str, Any]]) -> str:
        titles = []
        for i, s in enumerate(sources[:5], 1):
            title = s.get("title", "No title")
            source = s.get("source_type", "Unknown")
            titles.append(f"{i}. {title} ({source})")
        return (
            "I found relevant sources but encountered an error generating a summary.\n\n"
            + "\n".join(titles)
            + "\n\nPlease try again or rephrase your question."
        )
