"""
Tavily Search Tool — fetches articles from specialist timber sites or the open web.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.models import RetrievedSource
from agentic_rag.utils import parse_date, parse_min_date, with_year
from tavily import TavilyClient

logger = structlog.get_logger(__name__)

_SPECIALIST_DOMAINS: list[str] = [
    "globalwood.org",
    "timber-online.net",
    "agrarheute.com",
    "holzkurier.com",
    "forestmachinemagazine.com",
    "euwid-holz.de",
    "holz-zentralblatt.com",
    "fordaq.com",
]


def _is_too_old(result: dict[str, Any], min_date: datetime, specialist_only: bool = False) -> bool:
    """
    Returns True if the article should be dropped because it's too old.

    Specialist searches: undated articles from unknown domains are rejected (can't trust their age).
    Open-web searches: undated articles are kept — Tavily rarely includes dates for web results,
    but they're usually recent. The Verifier judges content recency instead.
    Dated articles: always compare against the hard cutoff date.
    """
    pub = parse_date(result.get("published_date"))
    if pub is None:
        if specialist_only:
            # Specialist search: only keep undated from trusted specialist domains
            url: str = result.get("url") or ""
            return not any(d in url for d in _SPECIALIST_DOMAINS)
        else:
            # Open-web search: allow undated (verifier LLM judges recency from content)
            return False
    return bool(pub < min_date)


def _to_source(result: dict[str, Any]) -> RetrievedSource | None:
    url = result.get("url")
    title = (result.get("title") or "").strip()
    content = (result.get("content") or "").strip()
    if not url or (not title and not content):
        return None
    return RetrievedSource(
        chunk_id="",
        article_id="",
        content=content,
        score=result.get("score", 0.5),
        source_type="tavily",
        source_name=result.get("source"),
        title=title,
        url=url,
        published_at=result.get("published_date"),
        keywords=[],
    )


class TavilySearchTool:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or agentic_settings.tavily_api_key
        if not key:
            logger.warning("Tavily API key not configured")
            self.client = None
        else:
            self.client = TavilyClient(api_key=key)
        # Pull the cutoff date from config so it's easy to change in one place
        self._min_date = parse_min_date(agentic_settings.min_allowed_evidence_date)

    def search(
        self,
        query: str,
        max_results: int | None = None,
        search_angles: list[str] | None = None,
        specialist_only: bool = False,
    ) -> list[RetrievedSource]:
        if not self.client:
            return []

        max_results = max_results or agentic_settings.tavily_max_results
        per_run = 2 if specialist_only else max(max_results // 2, 5)
        enriched = with_year(query)
        runs = self._build_runs(enriched, search_angles or [], specialist_only=specialist_only)

        seen_urls: set[str] = set()
        all_results: list[RetrievedSource] = []
        total_old = 0

        # Fire all search runs at once and collect results as they come in
        def _run_one(
            run_name: str, run_query: str, domains: list[str] | None
        ) -> tuple[str, list[RetrievedSource], int]:
            kept_list: list[RetrievedSource] = []
            old = 0
            is_specialist = domains is not None
            try:
                kwargs: dict[str, Any] = {
                    "query": run_query,
                    "max_results": per_run,
                    "search_depth": agentic_settings.tavily_search_depth,
                    "include_published_date": True,
                }
                if domains:
                    kwargs["include_domains"] = domains
                assert self.client is not None
                raw = self.client.search(**kwargs).get("results", [])
                for r in raw:
                    if _is_too_old(r, self._min_date, specialist_only=is_specialist):
                        old += 1
                        continue
                    source = _to_source(r)
                    if source:
                        kept_list.append(source)
            except Exception as exc:
                logger.error(f"Tavily {run_name} error: {exc}")
            return run_name, kept_list, old

        try:
            with ThreadPoolExecutor(max_workers=len(runs)) as pool:
                futures = [pool.submit(_run_one, name, q, domains) for name, q, domains in runs]
                for fut in as_completed(futures, timeout=10):
                    run_name, sources, old = fut.result(timeout=10)
                    total_old += old
                    kept = 0
                    for s in sources:
                        if not s.url or s.url not in seen_urls:
                            all_results.append(s)
                            if s.url:
                                seen_urls.add(s.url)
                            kept += 1
                    logger.info(f"Tavily {run_name}: {kept} kept | skipped_old={old}")
        except TimeoutError:
            logger.warning("Tavily: one or more search runs timed out after 10s")

        now = datetime.now(tz=UTC)
        all_results.sort(key=lambda s: self._rescore(s, self._min_date, now), reverse=True)

        logger.info(
            f"Tavily: {len(all_results)} articles across {len(runs)} parallel runs | "
            f"skipped_old={total_old}"
        )
        return all_results

    def _rescore(self, source: RetrievedSource, min_date: datetime, max_date: datetime) -> float:
        domain_score = (
            0.8 if any(d in (source.url or "") for d in _SPECIALIST_DOMAINS) else source.score
        )
        pub = parse_date(source.published_at)
        if pub:
            range_days = max((max_date - min_date).days, 1)
            days_old = (max_date - pub).days
            freshness = max(0.0, 1.0 - (days_old / range_days))
        else:
            freshness = 0.3
        return float(0.60 * domain_score + 0.40 * freshness)

    def _build_runs(
        self,
        query: str,
        search_angles: list[str],
        specialist_only: bool = False,
    ) -> list[tuple[str, str, list[str] | None]]:
        if specialist_only:
            return [(f"specialist-{domain}", query, [domain]) for domain in _SPECIALIST_DOMAINS]
        runs: list[tuple[str, str, list[str] | None]] = [
            ("open-web", query, None),
        ]
        for i, angle in enumerate(search_angles[:2], start=1):
            runs.append((f"angle-{i}", with_year(angle), None))
        return runs
