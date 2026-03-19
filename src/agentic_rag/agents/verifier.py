"""
Fact Verifier — reads through the ranked sources and picks what's actually useful.

The LLM goes through each article and decides whether it's relevant to the query.
It gets the Ranker's shortlist and hands back a cleaned-up list for the Synthesizer.
"""

from datetime import datetime
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.prompts.prompts_template import FACT_VERIFIER_PROMPT, format_sources_for_prompt
from agentic_rag.state import validate_node_state
from agentic_rag.utils import extract_token_cost
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)


class FactVerifier:
    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or ChatOpenAI(model=agentic_settings.verifier_model_name, temperature=0)

    def verify(self, state: dict[str, Any]) -> dict[str, Any]:
        state = validate_node_state(state, "verifier")
        sources = state.get("all_sources", [])
        query = state.get("query", "")
        today = datetime.now().strftime("%Y-%m-%d")
        cutoff = agentic_settings.min_allowed_evidence_date

        if not sources:
            logger.warning("No sources to verify")
            return {
                **state,
                "verified_sources": [],
                "key_facts": [],
                "evidence_summary": "No sources were retrieved.",
                "confidence_score": 0.0,
                "off_topic_indices": [],
                "steps": state.get("steps", []) + ["verification_no_sources"],
            }

        sources_to_verify = sources[: agentic_settings.max_sources_to_verify]
        formatted = format_sources_for_prompt(
            sources_to_verify,
            max_sources=agentic_settings.max_sources_to_verify,
            max_chars=agentic_settings.max_content_chars_per_source,
        )

        prompt = FACT_VERIFIER_PROMPT.format(
            query=query,
            sources=formatted,
            source_count=len(sources_to_verify),
            today=today,
            cutoff_date=cutoff,
        )

        tokens_in, tokens_out, cost = 0, 0, 0.0
        verified_sources: list[dict[str, Any]] = []
        key_facts: list[str] = []
        confidence = 0.3
        evidence_summary = ""
        off_topic_indices: list[int] = []

        try:
            response = self.llm.invoke(prompt)
            tokens_in, tokens_out, cost = extract_token_cost(
                response,
                agentic_settings.verifier_input_cost_per_token,
                agentic_settings.verifier_output_cost_per_token,
            )
            raw = JsonOutputParser().parse(response.content)
            reasoning = raw.get("reasoning", "")
            confidence = float(raw.get("overall_confidence", 0.3))
            key_facts = raw.get("key_facts", [])
            evidence_summary = raw.get("evidence_summary", "")
            off_topic_indices = raw.get("rejected_indices", [])
            selected_indices = raw.get("selected_indices", [])
            selected_source_details = {
                s["index"]: s
                for s in raw.get("selected_sources", [])
                if isinstance(s, dict) and "index" in s
            }
            for idx in selected_indices:
                source_idx = int(idx) - 1
                if 0 <= source_idx < len(sources_to_verify):
                    source = dict(sources_to_verify[source_idx])
                    detail = selected_source_details.get(int(idx), {})
                    source["relevance_reason"] = detail.get("relevance_reason", "")
                    source["llm_key_facts"] = detail.get("key_facts", [])
                    verified_sources.append(source)
            if reasoning:
                logger.info(f"  Verifier reasoning: {reasoning[:200]}")
        except Exception as exc:
            logger.error(f"Verification LLM error: {exc}")
            verified_sources = list(sources_to_verify)
            confidence = 0.25
            evidence_summary = "Verification failed — using all retrieved sources."

        logger.info(
            f"Verifier: {len(verified_sources)}/{len(sources_to_verify)} sources selected | "
            f"confidence={confidence:.2f} | facts={len(key_facts)}"
        )

        return {
            **state,
            "verified_sources": verified_sources,
            "key_facts": key_facts,
            "evidence_summary": evidence_summary,
            "confidence_score": round(confidence, 2),
            "off_topic_indices": off_topic_indices,
            "steps": state.get("steps", []) + [f"verified_{len(verified_sources)}_sources"],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "cost_usd": state.get("cost_usd", 0.0) + cost,
            "total_tokens": state.get("total_tokens", 0) + tokens_in + tokens_out,
        }
