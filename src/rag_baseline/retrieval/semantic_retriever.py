import logging

from rag_baseline.configuration import settings
from rag_baseline.custom_exceptions import EmbeddingError, VectorStoreError
from rag_baseline.domain_models import RetrievalResult
from rag_baseline.embedding.text_embedder import EmbeddingService
from rag_baseline.retrieval.retrieval_cache import RetrievalCache
from vector_store.qdrant import QdrantRepository

logger = logging.getLogger(__name__)


class SemanticRetriever:
    def __init__(self) -> None:
        self.embedding_generator: EmbeddingService = EmbeddingService()
        self.vector_store: QdrantRepository = QdrantRepository()
        self.cache: RetrievalCache = RetrievalCache()

    def retrieve(self, query: str) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks with error handling and fallback.

        Args:
            query: Search query

        Returns:
            List of retrieved results (may be empty on failure)
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to retriever")
            return []

        cached: list[RetrievalResult] | None = self.cache.get(query)
        if cached is not None:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached

        try:
            query_embedding = self.embedding_generator.embed(query)
        except EmbeddingError as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}")
            return []

        try:
            search_results = self.vector_store.search(
                query_embedding,
                settings.top_k_results,
            )
        except VectorStoreError as e:
            logger.error(f"Vector search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during vector search: {e}")
            return []

        results: list[RetrievalResult] = []

        try:
            for point in search_results:
                results.append(
                    RetrievalResult(
                        chunk_id=str(point.id),
                        article_id=str(point.payload["article_id"]),
                        content=str(point.payload["content"]),
                        similarity_score=float(point.score),
                        published_at=point.payload.get("published_at"),
                        source=point.payload.get("source"),
                        title=point.payload.get("title"),
                        url=point.payload.get("url"),
                        keywords=point.payload.get("keywords", []),
                    )
                )

            self.cache.set(query, results)
            return results

        except Exception as e:
            logger.error(f"Error processing search results: {e}")
            return []
