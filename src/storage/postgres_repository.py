import psycopg2
from rag_baseline.configuration import settings
from rag_baseline.custom_exceptions import StorageLayerError
from rag_baseline.domain_models import NewsArticle, TextChunk


class PostgresRepository:
    def __init__(self) -> None:
        self.connection = psycopg2.connect(settings.postgres_url)
        self.connection.autocommit = True

    def insert_article(self, article: NewsArticle) -> None:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO articles (
                        article_id,
                        title,
                        content,
                        source,
                        published_at,
                        url,
                        language,
                        country,
                        keywords
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (article_id) DO NOTHING;
                    """,
                    (
                        article.article_id,
                        article.title,
                        article.content,
                        article.source,
                        article.published_at,
                        article.url,
                        article.language,
                        article.country,
                        article.keywords,
                    ),
                )
        except Exception as error:
            raise StorageLayerError(f"Failed to insert article {article.article_id}") from error

    def insert_chunks(self, chunks: list[TextChunk]) -> None:
        try:
            with self.connection.cursor() as cursor:
                for chunk in chunks:
                    cursor.execute(
                        """
                        INSERT INTO chunks (
                            chunk_id,
                            article_id,
                            content,
                            chunk_index,
                            published_at,
                            source,
                            language,
                            keywords
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO NOTHING;
                        """,
                        (
                            chunk.chunk_id,
                            chunk.article_id,
                            chunk.content,
                            chunk.chunk_index,
                            chunk.published_at,
                            chunk.source,
                            chunk.language,
                            chunk.keywords,
                        ),
                    )
        except Exception as error:
            raise StorageLayerError("Failed to insert text chunks") from error

    def get_chunks_with_metadata(self, chunk_ids: list[str]) -> list[dict[str, object]]:
        if not chunk_ids:
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        c.chunk_id,
                        c.article_id,
                        c.content,
                        c.published_at,
                        c.source,
                        c.language,
                        c.keywords,
                        a.title,
                        a.url
                    FROM chunks c
                    JOIN articles a ON c.article_id = a.article_id
                    WHERE c.chunk_id = ANY(%s)
                    """,
                    (chunk_ids,),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "chunk_id": row[0],
                            "article_id": row[1],
                            "content": row[2],
                            "published_at": row[3],
                            "source": row[4],
                            "language": row[5],
                            "keywords": row[6],
                            "title": row[7],
                            "url": row[8],
                        }
                    )

                return results
        except Exception as error:
            raise StorageLayerError("Failed to fetch chunks with metadata") from error

    def get_all_chunks(self) -> list[TextChunk]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT chunk_id, article_id, content, chunk_index,
                           published_at, source, language, keywords
                    FROM chunks
                    ORDER BY article_id, chunk_index
                    """
                )

                chunks = []
                for row in cursor.fetchall():
                    chunks.append(
                        TextChunk(
                            chunk_id=row[0],
                            article_id=row[1],
                            content=row[2],
                            chunk_index=row[3],
                            published_at=row[4],
                            source=row[5],
                            language=row[6],
                            keywords=row[7] if row[7] else [],
                        )
                    )

                return chunks
        except Exception as error:
            raise StorageLayerError("Failed to fetch all chunks") from error

    def close(self) -> None:
        if self.connection:
            self.connection.close()
