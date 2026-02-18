import logging
from datetime import datetime, timedelta

import requests
from rag_baseline.configuration import settings
from rag_baseline.domain_models import NewsArticle

logger = logging.getLogger(__name__)


class MediaStackClient:
    BASE_URL = "http://api.mediastack.com/v1/news"

    TIMBER_KEYWORDS = [
        "Aufforstung",
        "Baugenehmigungen",
        "Bauholz",
        "Baukonjunktur",
        "Baukosten",
        "Biomasse",
        "CO2-Zertifikate",
        "Entwaldungsverordnung",
        "EUDR",
        "Exportverbot",
        "Forstwirtschaft",
        "Heizungsgesetz",
        "Holzexport",
        "Holzimport",
        "Holzmarkt",
        "Holzpreis",
        "Holzpreise",
        "Immobilienmarkt",
        "Leitzins",
        "Lieferkettengesetz",
        "Lumber",
        "Neubau",
        "Rohholz",
        "Rundholz",
        "Schadholz",
        "Schnittholz",
        "Sturmholz",
        "Timber",
        "US-Lumber",
        "Wohnungsbau",
        "Zinsentwicklung",
        "Sägewerk",
        "Borkenkäfer",
        "Waldschäden",
    ]

    def fetch_latest_articles(self, limit: int = 25, days_back: int = 30) -> list[NewsArticle]:
        all_articles: dict[str, NewsArticle] = {}
        keyword_map: dict[str, list[str]] = {}

        # Calculate date range - last 30 days only
        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Fetching articles from {date_from} to {date_to}")

        for keyword in self.TIMBER_KEYWORDS:
            logger.info(f"Fetching articles for keyword: '{keyword}'...")

            params = {
                "access_key": settings.mediastack_api_key,
                "keywords": keyword,
                "languages": "en,de",
                "limit": limit,
                "date": f"{date_from},{date_to}",
            }

            try:
                response = requests.get(self.BASE_URL, params=params)

                if response.status_code != 200:
                    logger.warning(f"Failed for keyword '{keyword}': {response.text}")
                    continue

                data = response.json().get("data", [])
                logger.info(f"  Got {len(data)} articles for '{keyword}'")

                for item in data:
                    url = item.get("url")
                    if not url:
                        continue

                    # Track keywords for the article
                    if url not in keyword_map:
                        keyword_map[url] = []
                    keyword_map[url].append(keyword)

                    if url in all_articles:
                        continue

                    text_content = item.get("content") or item.get("description")
                    if not text_content:
                        continue

                    try:
                        published_at = datetime.fromisoformat(
                            item["published_at"].replace("Z", "+00:00")
                        )
                    except (KeyError, ValueError):
                        continue

                    all_articles[url] = NewsArticle(
                        article_id=url,
                        title=item.get("title", "No title"),
                        content=text_content,
                        source=item.get("source", "unknown"),
                        published_at=published_at,
                        url=url,
                        language=item.get("language", "en"),
                        country=item.get("country", "unknown"),
                        keywords=keyword_map.get(url, []),
                    )

            except Exception as e:
                logger.warning(f"Error fetching keyword '{keyword}': {e}")
                continue

        articles = list(all_articles.values())
        logger.info(f"Total unique articles fetched ({date_from} to {date_to}): {len(articles)}")
        return articles
