from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsArticle:
    article_id: str
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    language: str = "en"
    country: str = "unknown"
    keywords: list[str] = field(default_factory=list)


@dataclass
class TextChunk:
    chunk_id: str
    article_id: str
    content: str
    chunk_index: int
    # Metadata from parent article
    published_at: datetime | None = None
    source: str | None = None
    language: str | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    chunk_id: str
    article_id: str
    content: str
    similarity_score: float
    # Metadata for filtering and display
    published_at: datetime | None = None
    source: str | None = None
    title: str | None = None
    url: str | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class GeneratedAnswer:
    answer_text: str
    cited_article_ids: list[str]
    sources: list[dict[str, object]] = field(default_factory=list)


@dataclass
class RetrievalFilters:
    """Filters for metadata-based retrieval"""

    date_from: datetime | None = None
    date_to: datetime | None = None
    sources: list[str] | None = None
    languages: list[str] | None = None
    keywords: list[str] | None = None
    min_score: float = 0.0
