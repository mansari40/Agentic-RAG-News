import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from rag_baseline.configuration import settings
from rag_baseline.custom_exceptions import ExternalAPIError
from rag_baseline.domain_models import NewsArticle
from rag_baseline.utils.retry_utils import retry_with_backoff
from requests.exceptions import ConnectionError, RequestException, Timeout

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

    @retry_with_backoff(  # type: ignore[misc]
        max_retries=3,
        initial_delay=2.0,
        backoff_factor=2.0,
        exceptions=(RequestException, Timeout, ConnectionError),
    )
    def _fetch_keyword(self, keyword: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch articles for a single keyword with retry logic"""
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)

            if response.status_code == 401:
                raise ExternalAPIError("Invalid MediaStack API key")
            elif response.status_code == 429:
                raise ExternalAPIError("MediaStack rate limit exceeded")
            elif response.status_code != 200:
                logger.warning(
                    f"MediaStack API error for '{keyword}': "
                    f"{response.status_code} - {response.text}"
                )
                return []

            data: list[dict[str, Any]] = response.json().get("data", [])
            return data

        except Timeout:
            logger.warning(f"Timeout fetching keyword '{keyword}'")
            raise
        except ConnectionError:
            logger.warning(f"Connection error fetching keyword '{keyword}'")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching keyword '{keyword}': {e}")
            return []

    def fetch_latest_articles(self, limit: int = 25, days_back: int = 30) -> list[NewsArticle]:
        """
        Fetch articles with error handling and graceful degradation.

        """
        all_articles: dict[str, NewsArticle] = {}
        keyword_map: dict[str, list[str]] = {}

        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Fetching articles from {date_from} to {date_to}")

        successful_keywords = 0
        failed_keywords = 0

        for keyword in self.TIMBER_KEYWORDS:
            params: dict[str, Any] = {
                "access_key": settings.mediastack_api_key,
                "keywords": keyword,
                "languages": "en,de",
                "limit": limit,
                "date": f"{date_from},{date_to}",
            }

            try:
                data = self._fetch_keyword(keyword, params)
                logger.info(f"  Got {len(data)} articles for '{keyword}'")
                successful_keywords += 1

                for item in data:
                    url = item.get("url")
                    if not url:
                        continue

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

            except ExternalAPIError as e:
                logger.error(f"API error for keyword '{keyword}': {e}")
                failed_keywords += 1
                if "Invalid" in str(e) or "key" in str(e).lower():
                    raise
            except Exception as e:
                logger.warning(f"Failed to fetch keyword '{keyword}': {e}")
                failed_keywords += 1
                continue

        articles = list(all_articles.values())
        logger.info(
            f"Fetched {len(articles)} unique articles "
            f"({successful_keywords} keywords succeeded, {failed_keywords} failed)"
        )

        if not articles and failed_keywords > 0:
            raise ExternalAPIError(
                f"Failed to fetch any articles ({failed_keywords} keywords failed)"
            )

        return articles
