"""
Source Ranker — quick pre-filter before the Verifier runs.
Skims through titles, dates, and the first 150 characters of each source,
then returns a shortlist of the best candidates so the Verifier doesn't have
to read everything.
"""

from datetime import date
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.prompts.prompts_template import RANKER_PROMPT
from agentic_rag.state import validate_node_state
from agentic_rag.utils import extract_token_cost
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)


class SourceRanker:
    """
    Scores all retrieved sources by likely relevance and returns
    the top-N for the Verifier to read more carefully.
    """

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or ChatOpenAI(model=agentic_settings.ranker_model_name, temperature=0)

    def rank(self, state: dict[str, Any]) -> dict[str, Any]:
        state = validate_node_state(state, "ranker")
        sources = state.get("all_sources", [])
        query = state.get("query", "")

        if not sources:
            return {
                **state,
                "ranked_sources": [],
                "steps": state.get("steps", []) + ["ranked_no_sources"],
            }

        top_n = self._dynamic_top_n(
            state.get("query_type", "simple"),
            state.get("complexity", "simple"),
        )
        max_to_rank = agentic_settings.max_sources_to_rank

        # If already within the verifier budget, skip ranking
        if len(sources) <= top_n:
            logger.info(f"Ranker: {len(sources)} sources <= top_n={top_n}, skipping LLM rank")
            return {
                **state,
                "ranked_sources": sources[:top_n],
                "steps": state.get("steps", []) + ["ranked_passthrough"],
            }

        candidates = sources[:max_to_rank]
        articles_text = self._format_for_ranking(candidates)

        cutoff_date = (
            state.get("cutoff_date_override") or agentic_settings.min_allowed_evidence_date
        )
        prompt = RANKER_PROMPT.format(
            query=query,
            top_n=top_n,
            articles=articles_text,
            today=date.today().isoformat(),
            cutoff_date=cutoff_date,
        )

        tokens_in, tokens_out, cost = 0, 0, 0.0
        ranked_sources = candidates[:top_n]  # fallback: insertion order

        try:
            response = self.llm.invoke(prompt)
            tokens_in, tokens_out, cost = extract_token_cost(
                response,
                agentic_settings.openai_input_cost_per_token,
                agentic_settings.openai_output_cost_per_token,
            )
            raw = JsonOutputParser().parse(response.content)
            # Support new ranked_articles format and old ranked_indices fallback
            if "ranked_articles" in raw:
                indices = [a["index"] for a in raw["ranked_articles"] if "index" in a]
            else:
                indices = raw.get("ranked_indices", [])
            if indices and isinstance(indices, list):
                ranked = []
                seen = set()
                for idx in indices:
                    i = int(idx) - 1
                    if 0 <= i < len(candidates) and i not in seen:
                        ranked.append(candidates[i])
                        seen.add(i)
                    if len(ranked) >= top_n:
                        break
                ranked_sources = ranked
        except Exception as exc:
            logger.error(f"Ranker LLM error: {exc}")

        logger.info(
            f"Ranker: {len(sources)} -> {len(ranked_sources)} sources | " f"cost=${cost:.6f}"
        )

        return {
            **state,
            "ranked_sources": ranked_sources,
            "steps": state.get("steps", []) + [f"ranked_{len(ranked_sources)}_sources"],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "cost_usd": state.get("cost_usd", 0.0) + cost,
            "total_tokens": state.get("total_tokens", 0) + tokens_in + tokens_out,
        }

    def _dynamic_top_n(self, query_type: str, complexity: str) -> int:
        """
        How many sources to hand off to the Verifier.

        Simple queries get fewer (less to verify), complex or multi-hop queries
        get more so the Verifier has enough to work with.

        query_type  | complexity  | top_n
        ------------|-------------|------
        simple      | simple      |  8
        simple      | moderate    | 10
        temporal    | any         | 12
        comparison  | any         | 12
        multi_hop   | any         | 15
        any         | complex     | 15
        """
        type_map = {"simple": 8, "temporal": 12, "comparison": 12, "multi_hop": 15}
        compl_map = {"simple": 8, "moderate": 10, "complex": 15}
        return max(
            type_map.get(query_type, 10),
            compl_map.get(complexity, 10),
        )

    def _format_for_ranking(self, sources: list[dict[str, Any]]) -> str:
        lines = []
        for i, s in enumerate(sources, 1):
            title = (s.get("title") or "No title")[:80]
            pub = s.get("published_at", "unknown date")
            content = (s.get("content") or "")[:150].replace("\n", " ")
            stype = s.get("source_type", "?")
            lines.append(f"[{i}] ({stype}) {title} | {pub}\n    {content}")
        return "\n\n".join(lines)
