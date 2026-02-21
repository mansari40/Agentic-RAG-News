import csv
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
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
        # German keywords
        "Holzpreis",
        "Holzpreise",
        "Rundholz",
        "Bauholz",
        "Schnittholz",
        "Sägewerk",
        "Holzmarkt",
        "Rohholz",
        "Borkenkäfer",
        "Schadholz",
        "Waldschäden",
        "Forstwirtschaft",
        "Aufforstung",
        "Sturmholz",
        "Baugenehmigungen",
        "Wohnungsbau",
        "Baukonjunktur",
        "Baukosten",
        "Neubau",
        "Zinsentwicklung",
        "Leitzins",
        "Immobilienmarkt",
        "EUDR",
        "Entwaldungsverordnung",
        "Lieferkettengesetz",
        "Heizungsgesetz",
        "Biomasse",
        "CO2-Zertifikate",
        "Exportverbot",
        # English keywords
        "Lumber",
        "Timber",
        "Softwood lumber",
        "Hardwood lumber",
        "Sawmill",
        "Bark beetle",
        "Salvage logging",
        "Wildfire impact",
        "Housing starts",
        "Building permits",
        "Mass timber",
        "CLT",
        "Lumber tariffs",
        "Log exports",
        "US-Lumber",
        "Holzexport",
        "Holzimport",
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

    def fetch_latest_articles(
        self, limit: int = 100, days_back: int = 30, export_csv: bool = True
    ) -> list[NewsArticle]:
        """
        Fetch latest articles (last 30 days by default)

        Args:
            limit: Max articles per keyword (100 = more data)
            days_back: How many days back to fetch (default 30)
            export_csv: Export results to CSV file

        Returns:
            List of unique NewsArticle objects
        """
        all_articles: dict[str, NewsArticle] = {}
        keyword_map: dict[str, list[str]] = {}

        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Fetching articles from {date_from} to {date_to}")

        successful_keywords = 0
        failed_keywords = 0
        total_keywords = len(self.TIMBER_KEYWORDS)

        for idx, keyword in enumerate(self.TIMBER_KEYWORDS, 1):
            # Progress logging
            logger.info(f"Processing keyword {idx}/{total_keywords}: '{keyword}'")

            # Add delay to avoid rate limiting
            if idx > 1:
                time.sleep(1.5)

            params: dict[str, Any] = {
                "access_key": settings.mediastack_api_key,
                "keywords": keyword,
                "languages": "en,de",
                "limit": limit,
                "date": f"{date_from},{date_to}",
                "sort": "published_desc",
            }

            try:
                data = self._fetch_keyword(keyword, params)
                logger.info(f"Got {len(data)} articles for '{keyword}'")
                successful_keywords += 1

                for item in data:
                    url = item.get("url")
                    if not url:
                        continue

                    # Track which keywords found this article
                    if url not in keyword_map:
                        keyword_map[url] = []
                    keyword_map[url].append(keyword)

                    # Skip if already processed
                    if url in all_articles:
                        continue

                    # Get content
                    text_content = item.get("content") or item.get("description")
                    if not text_content:
                        continue

                    # Parse date
                    try:
                        published_at = datetime.fromisoformat(
                            item["published_at"].replace("Z", "+00:00")
                        )
                    except (KeyError, ValueError):
                        continue

                    # Create article object
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

        # Summary logging
        logger.info("=" * 60)
        logger.info("INGESTION SUMMARY:")
        logger.info(f"  Total keywords processed: {total_keywords}")
        logger.info(f"  Successful: {successful_keywords}")
        logger.info(f"  Failed: {failed_keywords}")
        logger.info(f"  Unique articles: {len(articles)}")
        logger.info(f"  Date range: {date_from} to {date_to}")
        logger.info("=" * 60)

        # Export to CSV
        if export_csv and articles:
            self._export_to_csv(articles, date_from, date_to)

        if not articles and failed_keywords > 0:
            raise ExternalAPIError(
                f"Failed to fetch any articles ({failed_keywords} keywords failed)"
            )

        return articles

    def _export_to_csv(self, articles: list[NewsArticle], date_from: str, date_to: str) -> None:
        """Export articles to CSV file"""
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Generate filename with date range
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = data_dir / f"articles_{date_from}_to_{date_to}_{timestamp}.csv"

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "article_id",
                        "title",
                        "content",
                        "source",
                        "published_at",
                        "url",
                        "language",
                        "country",
                        "keywords",
                    ]
                )

                # Data rows
                for article in articles:
                    writer.writerow(
                        [
                            article.article_id,
                            article.title,
                            article.content,
                            article.source,
                            article.published_at.isoformat() if article.published_at else "",
                            article.url,
                            article.language,
                            article.country,
                            ", ".join(article.keywords) if article.keywords else "",
                        ]
                    )

            logger.info(f"Exported {len(articles)} articles to: {filename}")

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
