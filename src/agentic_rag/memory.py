"""
Conversation memory — keeps track of previous questions, answers, and a short-lived cache.
"""

from datetime import datetime, timedelta
from typing import Any

from agentic_rag.domain import is_timber_related

# Questions containing these words need fresh results every time — don't serve from cache
_TEMPORAL_BYPASS_KEYWORDS = {
    "latest",
    "recent",
    "today",
    "current",
    "now",
    "just",
    "breaking",
    "this week",
    "this month",
    "neue",
    "aktuell",
    "heute",
    "jetzt",
}

_FOLLOW_UP_INDICATORS = [
    "it",
    "they",
    "that company",
    "those",
    "the same",
    "what about",
    "how about",
    "more details",
    "explain more",
    "elaborate",
    "tell me more",
    "can you expand",
]


class ConversationMemory:
    """Stores conversation history and a cache across queries in the same session."""

    def __init__(self, max_history: int = 10, cache_ttl_minutes: int = 60) -> None:
        self.max_history = max_history
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.conversation_history: list[dict[str, Any]] = []
        self.query_cache: dict[str, dict[str, Any]] = {}
        self.failed_queries: list[str] = []
        self.session_cost_usd: float = 0.0
        self.session_total_tokens: int = 0

    def add_interaction(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        meta = metadata or {}
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer,
            "sources": sources,
            "metadata": meta,
            "cost_usd": meta.get("cost_usd", 0.0),
        }
        self.conversation_history.append(interaction)
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

        self.session_cost_usd += meta.get("cost_usd", 0.0)
        self.session_total_tokens += meta.get("total_tokens", 0)

        # Only cache queries that don't ask for "latest" or "current" information
        if not self._is_temporal_query(query):
            self.query_cache[query.lower().strip()] = {
                "answer": answer,
                "timestamp": datetime.now(),
            }

    def add_failed_query(self, query: str) -> None:
        self.failed_queries.append(query)

    def check_query_cache(self, query: str) -> dict[str, Any] | None:
        if self._is_temporal_query(query):
            return None

        key = query.lower().strip()
        entry = self.query_cache.get(key)
        if not entry:
            return None

        if datetime.now() - entry["timestamp"] > self.cache_ttl:
            del self.query_cache[key]
            return None

        return entry

    def _is_temporal_query(self, query: str) -> bool:
        query_lower = query.lower()
        return any(kw in query_lower for kw in _TEMPORAL_BYPASS_KEYWORDS)

    def is_follow_up_question(self, current_query: str) -> tuple[bool, dict[str, Any] | None]:
        if not self.conversation_history:
            return False, None

        last = self.conversation_history[-1]
        query_lower = current_query.lower().strip()
        words = current_query.split()

        has_indicator = any(ind in query_lower for ind in _FOLLOW_UP_INDICATORS)
        if len(words) <= 6 and has_indicator:
            return True, last

        if (
            len(words) <= 2
            and len(self.conversation_history) >= 1
            and is_timber_related(last.get("query", ""))
        ):
            return True, last

        return False, None

    def get_conversation_context(self, context_window: int = 3) -> str:
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-context_window:]
        lines = []
        for interaction in recent:
            answer_preview = interaction["answer"][:200]
            lines.append(f"Previous Q: {interaction['query']}\n" f"Previous A: {answer_preview}...")
        return "\n\n".join(lines)

    def get_previous_entities(self) -> list[str]:
        if not self.conversation_history:
            return []
        entities = self.conversation_history[-1].get("metadata", {}).get("entities", [])
        return entities if isinstance(entities, list) else []

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_interactions": len(self.conversation_history),
            "cached_queries": len(self.query_cache),
            "failed_queries": len(self.failed_queries),
            "session_cost_usd": round(self.session_cost_usd, 6),
            "session_total_tokens": self.session_total_tokens,
        }

    def get_session_cost(self) -> dict[str, Any]:
        return {
            "total_cost_usd": round(self.session_cost_usd, 6),
            "total_tokens": self.session_total_tokens,
            "total_queries": len(self.conversation_history),
            "avg_cost_per_query": round(
                self.session_cost_usd / max(len(self.conversation_history), 1), 6
            ),
        }

    def clear(self) -> None:
        self.conversation_history.clear()
        self.query_cache.clear()
        self.failed_queries.clear()
        self.session_cost_usd = 0.0
        self.session_total_tokens = 0
