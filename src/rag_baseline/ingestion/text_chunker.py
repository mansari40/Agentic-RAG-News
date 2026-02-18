import uuid

from rag_baseline.configuration import settings
from rag_baseline.domain_models import NewsArticle, TextChunk


class TextChunker:
    def chunk_article(self, article: NewsArticle) -> list[TextChunk]:
        content = article.content
        chunks = []

        start = 0
        index = 0

        while start < len(content):
            end = start + settings.chunk_size
            chunk_text = content[start:end]

            chunks.append(
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    article_id=article.article_id,
                    content=chunk_text,
                    chunk_index=index,
                    published_at=article.published_at,
                    source=article.source,
                    language=article.language,
                    keywords=article.keywords,
                )
            )

            start += settings.chunk_size - settings.chunk_overlap
            index += 1

        return chunks
