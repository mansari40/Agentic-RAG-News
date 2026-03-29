from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import requests
import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.models import RetrievedSource
from agentic_rag.utils import parse_date, parse_min_date

logger = structlog.get_logger(__name__)

_KEYWORD_GROUPS: dict[str, list[str]] = {
    # Price terms — highest relevance, always fetched
    "price": ["Holzpreis", "Holzpreise", "Schnittholzpreise", "Bauholz", "Rohholz"],
    # Species names — dominate German timber headlines, so always included
    "species": ["Fichte", "Fichtenholz", "Kiefernholz", "Nadelholz", "Schnittholz"],
    # Forest supply chain — Borkenkäfer and Forstwirtschaft return the most results
    "supply": [
        "Borkenkäfer",
        "Forstwirtschaft",
        "Waldschäden",
        "Waldsterben",
        "Schadholz",
        "Sturmholz",
    ],
    # Sawmill and processing
    "sawmill": ["Sägewerk", "Sägeindustrie"],
    # General market and industry terms
    "market": ["Holzmarkt", "Holzwirtschaft"],
    # Trade — Zölle is high volume
    "trade": ["Zölle", "Holzexport", "Holzimport"],
    # Policy and sustainability
    "policy": ["EUDR", "Lieferkettengesetz", "Entwaldungsverordnung", "Aufforstung"],
    # Wood used as fuel
    "energy": ["Holzpellets", "Biomasse"],
    # Construction demand — broad but directly tied to timber consumption
    "construction": [
        "Wohnungsbau",
        "Baugenehmigungen",
        "Neubau",
        "Baukosten",
        "Baukonjunktur",
        "Holzbau",
    ],
    # Wider economic context
    "context": ["Immobilienmarkt", "Heizungsgesetz"],
    # Price outlook and forecasts — triggered for forward-looking queries
    "outlook": ["Preisentwicklung", "Holzpreisprognose", "Marktausblick", "Konjunktur"],
    # English fallback — only "Mass timber" works well here.
    "fallback_en": ["Mass timber"],
}

# Articles containing any of these strings are always dropped — they're off-topic noise
_HARD_NOISE: frozenset[str] = frozenset(
    {
        "kreuzfahrtschiff",
        "stradivari",
        "secured term loan",
        "massive blaze",
        "warehouse fire",
        "zigaretten",
        "tabak",
    }
)

# These keywords are too broad
_BROAD_KEYWORDS: frozenset[str] = frozenset(
    {
        "wohnungsbau",
        "baukonjunktur",
        "baugenehmigungen",
        "holzbau",
        "neubau",
        "baukosten",
        "heizungsgesetz",
        "immobilienmarkt",
        "zölle",
        "mass timber",
        "traceability",
        "supply chain disruptions",
        "timber",
        "lumber",
    }
)

_BROAD_LIMIT = 7
_SPECIFIC_LIMIT = 25


class MediaStackAPITool:
    BASE_URL = "http://api.mediastack.com/v1/news"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or agentic_settings.mediastack_api_key
        if not self.api_key:
            logger.warning("MediaStack API key not configured")
        self._min_date = parse_min_date(agentic_settings.min_allowed_evidence_date)

    def search(self, query: str, max_results: int | None = None) -> list[RetrievedSource]:
        if not self.api_key:
            return []

        max_results = max_results or agentic_settings.mediastack_max_results

        # Use _min_date directly — it is updated per-request by the researcher
        # to match the user's chosen date_from from the left bar
        date_from = self._min_date.strftime("%Y-%m-%d")
        date_to = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        keywords = self._build_keyword_plan(query)
        logger.info(f"MediaStack fetching: {len(keywords)} keywords | range={date_from}->{date_to}")

        seen: dict[str, RetrievedSource] = {}
        for kw in keywords:
            if len(seen) >= max_results:
                break
            limit = _BROAD_LIMIT if kw.lower() in _BROAD_KEYWORDS else _SPECIFIC_LIMIT
            self._fetch(kw, date_from, date_to, min(limit, 25), seen)

        result = list(seen.values())[:max_results]
        logger.info(f"MediaStack: {len(result)} articles fetched")
        return result

    def _fetch(
        self,
        keyword: str,
        date_from: str,
        date_to: str,
        limit: int,
        seen: dict[str, RetrievedSource],
    ) -> None:
        params = {
            "access_key": self.api_key,
            "keywords": keyword,
            "offset": 0,
            "limit": limit,
            "sort": "published_desc",
            "date": f"{date_from},{date_to}",
            "countries": agentic_settings.mediastack_countries,
            "languages": "de,en",
        }
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"MediaStack HTTP {resp.status_code} kw='{keyword}'")
                return
            items = resp.json().get("data", [])
            fetched = 0
            for item in items[:limit]:
                source = self._to_source(item, keyword)
                if source and source.url and source.url not in seen:
                    seen[source.url] = source
                    fetched += 1
            logger.info(f"MediaStack: {fetched} raw articles for kw='{keyword}'")
        except requests.exceptions.Timeout:
            logger.warning(f"MediaStack timeout kw='{keyword}'")
        except Exception as exc:
            logger.error(f"MediaStack error kw='{keyword}': {exc}")

    def _to_source(self, item: dict[str, Any], keyword: str) -> RetrievedSource | None:
        url = item.get("url")
        title = (item.get("title") or "").strip()
        description = (item.get("description") or "").strip()
        content = (item.get("content") or description).strip()
        published_raw = item.get("published_at")

        if not url or (not title and not content):
            return None

        pub = parse_date(published_raw)
        if pub is None or pub < self._min_date:
            return None

        combined = f"{title} {content}".lower()
        if any(h in combined for h in _HARD_NOISE):
            return None

        try:
            netloc = urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            netloc = ""

        return RetrievedSource(
            chunk_id="",
            article_id="",
            content=content,
            score=0.5,
            source_type="mediastack",
            source_name=item.get("source", netloc or "mediastack"),
            title=title,
            url=url,
            published_at=published_raw,
            language=item.get("language"),
            country=item.get("country"),
            keywords=[keyword],
        )

    def _build_keyword_plan(self, query: str) -> list[str]:
        """
        Build a keyword list for the query.
        Topic-matched keywords fill first; generic fillers take remaining slots.
        Max 13 keywords — enough for good coverage without too many API calls.
        """
        q = query.lower()
        topic: list[str] = []  # query-matched — highest priority, always first
        filler: list[str] = []  # generic fallbacks — fill remaining slots only

        # --- Topic-triggered groups (all go into `topic`) ---
        if any(
            t in q
            for t in [
                "eudr",
                "entwald",
                "regulation",
                "lieferkette",
                "deforestation",
                "aufforst",
                "traceability",
                "compliance",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["policy"])
        if any(
            t in q
            for t in [
                "price",
                "preis",
                "cost",
                "margin",
                "forecast",
                "bauholz",
                "schnittholz",
                "nadelholz",
                "fichte",
                "kiefer",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["price"])
        if any(
            t in q
            for t in [
                "supply",
                "bark beetle",
                "borkenkäfer",
                "forest",
                "rohholz",
                "schadholz",
                "sturmholz",
                "waldsterben",
                "dieback",
                "forstwirtschaft",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["supply"])
        if any(t in q for t in ["sawmill", "sägewerk", "sägeindustrie", "production"]):
            topic.extend(_KEYWORD_GROUPS["sawmill"])
        if any(
            t in q
            for t in [
                "export",
                "import",
                "trade",
                "tariff",
                "zölle",
                "zoll",
                "supply chain",
                "disruption",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["trade"])
        if any(t in q for t in ["pellet", "energy", "biomass", "biomasse", "heating", "heizung"]):
            topic.extend(_KEYWORD_GROUPS["energy"])
        if any(
            t in q
            for t in [
                "outlook",
                "forecast",
                "expect",
                "decline",
                "consequence",
                "impact",
                "affect",
                "effect",
                "result",
                "prognose",
                "ausblick",
                "entwicklung",
                "rückgang",
                "erwarten",
                "einfluss",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["outlook"])
        if any(
            t in q
            for t in [
                "housing",
                "construction",
                "wohnungsbau",
                "baugenehmigung",
                "neubau",
                "holzbau",
                "baukosten",
                "baukonjunktur",
                "building",
            ]
        ):
            topic.extend(_KEYWORD_GROUPS["construction"])
        if any(
            t in q for t in ["demand", "nachfrage", "immobilien", "heizung", "trend", "outlook"]
        ):
            topic.extend(_KEYWORD_GROUPS["context"])

        # --- Generic fillers (only consume slots not already taken by topic keywords) ---
        filler.extend(_KEYWORD_GROUPS["price"])
        filler.extend(_KEYWORD_GROUPS["species"])
        filler.extend(_KEYWORD_GROUPS["market"])
        filler.extend(_KEYWORD_GROUPS["construction"])
        filler.extend(_KEYWORD_GROUPS["fallback_en"])

        # Deduplicate preserving order — topic first, fillers after
        seen: set[str] = set()
        plan: list[str] = []
        for kw in topic + filler:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                plan.append(kw)

        return plan[:13]
