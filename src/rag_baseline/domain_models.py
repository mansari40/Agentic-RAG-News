from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsArticle:
    article_id: str
    title: str
    content: str
    source: str
    published_at: datetime
    url: str


@dataclass
class TextChunk:
    chunk_id: str
    article_id: str
    content: str
    chunk_index: int


@dataclass
class RetrievalResult:
    chunk_id: str
    article_id: str
    content: str
    similarity_score: float


@dataclass
class GeneratedAnswer:
    answer_text: str
    cited_article_ids: list[str]
