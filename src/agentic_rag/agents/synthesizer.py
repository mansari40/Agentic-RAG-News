"""
Answer Synthesizer — writes the final answer from verified sources.

After synthesis, a small LLM call checks whether a second research pass would
actually improve the answer. If it would, it sets needs_refinement=True and
writes a specific hint about what to search for next.
"""

import json
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.generation.answer_generator import AgenticAnswerGenerator
from agentic_rag.prompts.prompts_template import OUT_OF_SCOPE_RESPONSE, REFINEMENT_EVAL_PROMPT
from agentic_rag.state import validate_node_state
from agentic_rag.utils import extract_token_cost
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)


class AnswerSynthesizer:
    """Writes the final answer using whatever the Verifier approved."""

    def __init__(
        self,
        generator: AgenticAnswerGenerator | None = None,
        eval_llm: BaseChatModel | None = None,
    ) -> None:
        self.generator = generator or AgenticAnswerGenerator()
        self._eval_llm = eval_llm or ChatOpenAI(
            model=agentic_settings.chat_model_name, temperature=0
        )

    def synthesize(self, state: dict[str, Any]) -> dict[str, Any]:
        state = validate_node_state(state, "synthesizer")
        query = state.get("query", "")
        verified_sources = state.get("verified_sources", [])
        key_facts = state.get("key_facts", [])
        is_domain_relevant = state.get("is_domain_relevant", True)
        confidence = state.get("confidence_score", 0.5)
        query_type = state.get("query_type", "simple")
        refinement_count = state.get("refinement_count", 0)

        # Out of scope
        if not is_domain_relevant:
            logger.info("Query out of scope — returning scoped response")
            return {
                **state,
                "answer": OUT_OF_SCOPE_RESPONSE,
                "citations": [],
                "needs_refinement": False,
                "refinement_hint": "",
                "steps": state.get("steps", []) + ["out_of_scope"],
            }

        # No sources at all
        if not verified_sources:
            logger.warning("No verified sources for synthesis")
            no_sources_answer = (
                "I couldn't find relevant recent information about the German timber market "
                "for your question. This may be because the topic is very specific or "
                "recent news coverage is limited. Please try rephrasing your question."
            )
            # Even with no sources, attempt a refinement if budget allows
            needs_ref, ref_hint, eval_cost, eval_tokens = self._evaluate_for_refinement(
                query=query,
                answer=no_sources_answer,
                confidence=0.0,
                key_facts=[],
                evidence_summary="",
                sources_count=0,
                refinement_count=refinement_count,
            )
            return {
                **state,
                "answer": no_sources_answer,
                "citations": [],
                "needs_refinement": needs_ref,
                "refinement_hint": ref_hint,
                "refinement_count": refinement_count + (1 if needs_ref else 0),
                "cost_usd": state.get("cost_usd", 0.0) + eval_cost,
                "total_tokens": state.get("total_tokens", 0) + eval_tokens,
                "steps": state.get("steps", []) + ["synthesis_no_sources"],
            }

        logger.info(f"Synthesizing from {len(verified_sources)} verified sources")

        try:
            answer = self.generator.generate(
                query=query,
                sources=verified_sources,
                key_facts=key_facts,
                max_tokens=agentic_settings.max_synthesis_tokens,
                query_type=query_type,
                confidence_score=confidence,
            )
        except Exception as exc:
            logger.error(f"Synthesis error: {exc}")
            answer = "I encountered an error generating the answer. Please try again."

        cost = state.get("cost_usd", 0.0) + self.generator.last_call_cost
        total_tokens = state.get("total_tokens", 0) + self.generator.last_call_tokens

        # Refinement evaluation
        needs_ref, ref_hint, eval_cost, eval_tokens = self._evaluate_for_refinement(
            query=query,
            answer=answer,
            confidence=confidence,
            key_facts=key_facts,
            evidence_summary=state.get("evidence_summary", ""),
            sources_count=len(verified_sources),
            refinement_count=refinement_count,
        )
        cost += eval_cost
        total_tokens += eval_tokens

        step_label = "answer_refined" if refinement_count > 0 else "answer_synthesized"

        return {
            **state,
            "answer": answer,
            "citations": verified_sources[: agentic_settings.max_sources_to_synthesize],
            "needs_refinement": needs_ref,
            "refinement_hint": ref_hint,
            "refinement_count": refinement_count + (1 if needs_ref else 0),
            "steps": state.get("steps", []) + [step_label],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "cost_usd": cost,
            "total_tokens": total_tokens,
        }

    # Private helpers

    def _evaluate_for_refinement(
        self,
        query: str,
        answer: str,
        confidence: float,
        key_facts: list[str],
        evidence_summary: str,
        sources_count: int,
        refinement_count: int,
    ) -> tuple[bool, str, float, int]:
        """
        Decide whether another research pass would make the answer noticeably better.

        Returns (needs_refinement, refinement_hint, cost_usd, tokens_used).
        Checks a quick heuristic first to avoid an LLM call when the answer is already good.
        """
        # Stop if we've already done the max number of refinements
        if refinement_count >= agentic_settings.max_refinement_iterations:
            logger.info(f"Refinement eval: budget exhausted (count={refinement_count}), skipping")
            return False, "", 0.0, 0

        # Already got good confidence and enough sources — no need to refine
        if confidence >= 0.55 and sources_count >= 2:
            logger.info(
                f"Refinement eval: fast-path pass (confidence={confidence:.2f}, "
                f"sources={sources_count}) — evidence sufficient"
            )
            return False, "", 0.0, 0

        # If evidence is thin, fall through to the LLM call so the hint is specific

        logger.info(
            f"Refinement eval: calling LLM (confidence={confidence:.2f}, "
            f"sources={sources_count}, refinement_count={refinement_count})"
        )

        try:
            prompt = REFINEMENT_EVAL_PROMPT.format(
                query=query,
                answer=answer[:600],
                evidence_summary=(evidence_summary or "")[:300],
                confidence_score=round(confidence, 2),
                key_facts_count=len(key_facts),
                sources_count=sources_count,
            )
            response = self._eval_llm.invoke([HumanMessage(content=prompt)])
            raw = (response.content or "").strip()

            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

            parsed = json.loads(raw)
            needs_ref = bool(parsed.get("needs_refinement", False))
            ref_hint = (parsed.get("refinement_hint") or "").strip()

            t_in, t_out, cost = extract_token_cost(
                response,
                agentic_settings.openai_input_cost_per_token,
                agentic_settings.openai_output_cost_per_token,
            )
            logger.info(
                f"Refinement eval: needs_refinement={needs_ref} | "
                f"hint='{ref_hint[:80]}' | cost=${cost:.6f}"
            )
            return needs_ref, ref_hint, cost, t_in + t_out

        except Exception as exc:
            logger.warning(f"Refinement eval failed ({exc}) — using confidence fallback")
            # Fall back to a simple rule: only refine if confidence is very low and we have no facts
            needs_ref = confidence < 0.35 and len(key_facts) == 0
            return needs_ref, "", 0.0, 0
