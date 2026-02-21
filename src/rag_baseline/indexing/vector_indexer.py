from typing import Any

from rag_baseline.embedding.text_embedder import EmbeddingService
from storage.postgres_repository import PostgresRepository
from vector_store.qdrant import QdrantRepository


class VectorIndexingPipeline:
    def __init__(self, batch_size: int = 100) -> None:
        self.repository: PostgresRepository = PostgresRepository()
        self.vector_store: QdrantRepository = QdrantRepository()
        self.embedding_generator: EmbeddingService = EmbeddingService()
        self.batch_size = batch_size

    def index_all_chunks(self) -> None:
        chunks = self._fetch_all_chunks()

        if not chunks:
            print("No chunks found to index.")
            return

        # Create collection
        sample_embedding = self.embedding_generator.embed(chunks[0]["content"])
        vector_size = len(sample_embedding)
        self.vector_store.create_collection_if_not_exists(vector_size)

        # Process in batches
        total_chunks = len(chunks)
        print(f"Indexing {total_chunks} chunks in batches of {self.batch_size}...")

        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

            ids: list[str] = []
            vectors: list[list[float]] = []
            payloads: list[dict[str, Any]] = []

            for chunk in batch:
                embedding = self.embedding_generator.embed(chunk["content"])

                ids.append(chunk["chunk_id"])
                vectors.append(embedding)
                payloads.append(
                    {
                        "article_id": chunk["article_id"],
                        "content": chunk["content"],
                        "published_at": chunk["published_at"].isoformat()
                        if chunk["published_at"]
                        else None,
                        "source": chunk["source"],
                        "language": chunk["language"],
                        "keywords": chunk["keywords"],
                        "title": chunk["title"],
                        "url": chunk["url"],
                    }
                )

            # Upsert batch
            self.vector_store.upsert_vectors(ids, vectors, payloads)
            print(f"Batch {batch_num} indexed successfully")

        print(f"Indexing complete! {total_chunks} chunks indexed.")

    def _fetch_all_chunks(self) -> list[dict[str, Any]]:
        with self.repository.connection.cursor() as cursor:
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
                ORDER BY c.chunk_id;
                """
            )

            rows = cursor.fetchall()

            chunks = []
            for row in rows:
                chunks.append(
                    {
                        "chunk_id": row[0],
                        "article_id": row[1],
                        "content": row[2],
                        "published_at": row[3],
                        "source": row[4],
                        "language": row[5],
                        "keywords": row[6] if row[6] else [],
                        "title": row[7],
                        "url": row[8],
                    }
                )

            return chunks
