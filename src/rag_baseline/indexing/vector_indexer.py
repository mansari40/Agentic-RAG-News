from typing import Any, cast

from rag_baseline.embedding.text_embedder import EmbeddingService
from rag_baseline.storage.postgres_repository import PostgresRepository
from rag_baseline.vector_store.qdrant import QdrantRepository


class VectorIndexingPipeline:
    def __init__(self) -> None:
        self.repository: PostgresRepository = PostgresRepository()
        self.vector_store: QdrantRepository = QdrantRepository()
        self.embedding_generator: EmbeddingService = EmbeddingService()

    def index_all_chunks(self) -> None:
        chunks = self._fetch_all_chunks()

        if not chunks:
            return

        sample_embedding = self.embedding_generator.embed(chunks[0][2])
        vector_size = len(sample_embedding)

        self.vector_store.create_collection_if_not_exists(vector_size)

        ids: list[str] = []
        vectors: list[list[float]] = []
        payloads: list[dict[str, Any]] = []

        for chunk_id, article_id, content in chunks:
            embedding = self.embedding_generator.embed(content)

            ids.append(chunk_id)
            vectors.append(embedding)
            payloads.append(
                {
                    "article_id": article_id,
                    "content": content,
                }
            )

        self.vector_store.upsert_vectors(ids, vectors, payloads)

    def _fetch_all_chunks(self) -> list[tuple[str, str, str]]:
        with self.repository.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT chunk_id, article_id, content
                FROM chunks;
                """
            )

            rows = cursor.fetchall()

            return cast(list[tuple[str, str, str]], rows)
