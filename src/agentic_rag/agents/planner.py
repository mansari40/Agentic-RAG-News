"""
Query Planner — figures out what the user is asking before we start searching.

One LLM call that classifies intent, checks if the question is relevant to our
domain, and picks the query type and research mode. The Researcher then decides
which specific tools to call.
"""

from datetime import datetime
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.domain import is_timber_related
from agentic_rag.models import QueryPlan
from agentic_rag.prompts.prompts_template import QUERY_PLANNER_PROMPT
from agentic_rag.state import validate_node_state
from agentic_rag.utils import extract_token_cost
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)

_VALID_RESEARCH_MODES = frozenset({"full_research", "skip_research"})
_VALID_QUERY_TYPES = frozenset({"simple", "comparison", "temporal", "multi_hop"})
_VALID_COMPLEXITY = frozenset({"simple", "moderate", "complex"})


class QueryPlanner:
    """
    Does intent classification and research planning in a single LLM call.
    The result (a QueryPlan) drives everything downstream.
    """

    def __init__(self, memory: Any | None = None, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or ChatOpenAI(model=agentic_settings.chat_model_name, temperature=0)
        self.memory = memory

    def plan(self, state: dict[str, Any]) -> dict[str, Any]:
        state = validate_node_state(state, "planner")
        query = (state.get("query") or "").strip()
        today = datetime.now().strftime("%Y-%m-%d")
        context_section = self._build_context(query)

        prompt = QUERY_PLANNER_PROMPT.format(
            query=query,
            context_section=context_section,
            today=today,
            cutoff_date=agentic_settings.min_allowed_evidence_date,
        )

        tokens_in, tokens_out, cost = 0, 0, 0.0
        try:
            response = self.llm.invoke(prompt)
            tokens_in, tokens_out, cost = extract_token_cost(
                response,
                agentic_settings.openai_input_cost_per_token,
                agentic_settings.openai_output_cost_per_token,
            )
            raw = JsonOutputParser().parse(response.content)
            qplan = QueryPlan(**self._normalise(raw, query))
        except Exception as exc:
            logger.error(f"Planner LLM error: {exc}")
            qplan = self._fallback_plan(query)

        logger.info(
            f"Planner: intent={qplan.intent} | relevant={qplan.is_domain_relevant} | "
            f"type={qplan.query_type} | mode={qplan.research_mode}"
        )

        complexity_map = {"simple": 0.2, "moderate": 0.5, "complex": 0.8}
        return {
            **state,
            "query": query,
            "query_plan": qplan.model_dump(),
            "intent": qplan.intent,
            "query_type": qplan.query_type,
            "entities": qplan.entities,
            "sub_queries": [query] + qplan.search_angles[:2],
            "search_angles": qplan.search_angles,
            "temporal_info": qplan.temporal_info,
            "complexity": qplan.complexity,
            "complexity_score": complexity_map.get(qplan.complexity, 0.5),
            "is_follow_up": qplan.is_follow_up,
            "is_domain_relevant": qplan.is_domain_relevant,
            "domain_relevance_reason": qplan.domain_relevance_reason,
            "research_mode": qplan.research_mode,
            "use_hybrid": True,
            "top_k": agentic_settings.baseline_top_k,
            "steps": state.get("steps", []) + ["planned"],
            "llm_calls": state.get("llm_calls", 0) + 1,
            "cost_usd": state.get("cost_usd", 0.0) + cost,
            "total_tokens": state.get("total_tokens", 0) + tokens_in + tokens_out,
        }

    def _build_context(self, query: str) -> str:
        if not self.memory:
            return ""
        is_follow_up, prev = self.memory.is_follow_up_question(query)
        if is_follow_up and prev:
            return (
                f"\nCONVERSATION CONTEXT:\n"
                f"Previous Query: {prev['query']}\n"
                f"Previous Answer: {prev['answer'][:300]}...\n"
            )
        ctx = self.memory.get_conversation_context(context_window=2)
        return f"\nCONVERSATION CONTEXT:\n{ctx}" if ctx else ""

    def _normalise(self, raw: dict[str, Any], query: str) -> dict[str, Any]:
        r = dict(raw) if isinstance(raw, dict) else {}
        r["intent"] = r.get("intent", "domain")
        if r["intent"] not in {"conversational", "domain"}:
            r["intent"] = "domain"
        r["is_domain_relevant"] = bool(r.get("is_domain_relevant", True))
        r["is_follow_up"] = bool(r.get("is_follow_up", False))
        qt = r.get("query_type", "simple")
        r["query_type"] = qt if qt in _VALID_QUERY_TYPES else "simple"
        # If the LLM missed obvious recency words, bump the type to temporal ourselves
        _TEMPORAL_SIGNALS = {
            "latest",
            "recent",
            "current",
            "news",
            "today",
            "now",
            "this week",
            "this month",
            "update",
            "just",
            "newest",
        }
        if r["query_type"] == "simple" and any(s in query.lower() for s in _TEMPORAL_SIGNALS):
            r["query_type"] = "temporal"
        mode = r.get("research_mode", "full_research")
        r["research_mode"] = mode if mode in _VALID_RESEARCH_MODES else "full_research"
        complexity = r.get("complexity", "moderate")
        r["complexity"] = complexity if complexity in _VALID_COMPLEXITY else "moderate"
        if not isinstance(r.get("entities"), list):
            r["entities"] = []
        if not isinstance(r.get("search_angles"), list) or not r["search_angles"]:
            r["search_angles"] = [query]
        if not isinstance(r.get("domain_relevance_reason"), str):
            r["domain_relevance_reason"] = ""
        if not isinstance(r.get("temporal_info"), dict):
            r["temporal_info"] = None
        cr = r.get("conversational_response")
        r["conversational_response"] = str(cr) if cr else None
        return r

    def _fallback_plan(self, query: str) -> QueryPlan:
        is_news = any(h in query.lower() for h in {"latest", "recent", "news", "current", "today"})
        return QueryPlan(
            intent="domain",
            is_domain_relevant=is_timber_related(query),
            domain_relevance_reason="fallback — planner LLM error",
            query_type="temporal" if is_news else "simple",
            search_angles=[query, f"German timber market {query}"],
            research_mode="full_research",
            complexity="moderate",
        )
