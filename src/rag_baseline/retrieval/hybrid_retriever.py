import logging
from typing import Any

from rag_baseline.configuration import settings
from rag_baseline.custom_exceptions import EmbeddingError, VectorStoreError
from rag_baseline.domain_models import RetrievalResult
from rag_baseline.embedding.text_embedder import EmbeddingService
from rag_baseline.retrieval.keyword_searcher import KeywordSearcher
from rag_baseline.retrieval.retrieval_cache import RetrievalCache
from storage.postgres_repository import PostgresRepository
from vector_store.qdrant import QdrantRepository

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines semantic (vector) and keyword search with RRF fusion"""

    def __init__(self) -> None:
        self.embedding_generator: EmbeddingService = EmbeddingService()
        self.vector_store: QdrantRepository = QdrantRepository()
        self.cache: RetrievalCache = RetrievalCache()
        self.keyword_searcher: KeywordSearcher | None = None
        self.all_chunks: list[dict[str, Any]] = []
        self.postgres = PostgresRepository()

    def _initialize_keyword_search(self) -> None:
        """Lazy initialization of keyword search index"""
        if self.keyword_searcher is not None:
            return

        logger.info("Initializing keyword search index...")
        chunks = self.postgres.get_all_chunks()

        self.all_chunks = []
        for chunk in chunks:
            self.all_chunks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "article_id": chunk.article_id,
                    "content": chunk.content,
                    "published_at": chunk.published_at,
                    "source": chunk.source,
                    "title": getattr(chunk, "title", None),
                    "url": getattr(chunk, "url", None),
                    "keywords": chunk.keywords if hasattr(chunk, "keywords") else [],
                }
            )

        self.keyword_searcher = KeywordSearcher()
        self.keyword_searcher.fit(self.all_chunks)
        logger.info(f"Keyword search index built with {len(self.all_chunks)} chunks")

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[RetrievalResult],
        keyword_scores: dict[str, float],
        k: int = 60,
    ) -> list[RetrievalResult]:
        """Merge vector and keyword results using Reciprocal Rank Fusion"""
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.chunk_id
            rrf_scores[chunk_id] = 1.0 / (k + rank)
            result_map[chunk_id] = result

        sorted_keyword = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (chunk_id, _) in enumerate(sorted_keyword, 1):
            if chunk_id in rrf_scores:
                rrf_scores[chunk_id] += 1.0 / (k + rank)
            else:
                rrf_scores[chunk_id] = 1.0 / (k + rank)

                chunk_data = next((c for c in self.all_chunks if c["chunk_id"] == chunk_id), None)
                if chunk_data:
                    result_map[chunk_id] = RetrievalResult(
                        chunk_id=chunk_id,
                        article_id=chunk_data["article_id"],
                        content=chunk_data["content"],
                        similarity_score=0.0,
                        published_at=chunk_data.get("published_at"),
                        source=chunk_data.get("source"),
                        title=chunk_data.get("title"),
                        url=chunk_data.get("url"),
                        keywords=chunk_data.get("keywords", []),
                    )

        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_chunk_ids = [chunk_id for chunk_id, _ in sorted_results[: settings.top_k_results]]

        final_results = []
        for chunk_id in top_chunk_ids:
            if chunk_id in result_map:
                result = result_map[chunk_id]
                result.similarity_score = rrf_scores[chunk_id]
                final_results.append(result)

        return final_results

    def retrieve(self, query: str, use_hybrid: bool = True) -> list[RetrievalResult]:
        """
        Retrieve with hybrid search (vector + keyword) or pure semantic search.

        Args:
            query: Search query
            use_hybrid: If True, use hybrid search; if False, use only vector search

        Returns:
            List of retrieved results
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
            vector_results_raw = self.vector_store.search(
                query_embedding,
                settings.top_k_results * 2 if use_hybrid else settings.top_k_results,
            )
        except VectorStoreError as e:
            logger.error(f"Vector search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during vector search: {e}")
            return []

        vector_results: list[RetrievalResult] = []
        try:
            for point in vector_results_raw:
                vector_results.append(
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
        except Exception as e:
            logger.error(f"Error processing vector search results: {e}")
            return []

        if not use_hybrid:
            self.cache.set(query, vector_results)
            return vector_results

        try:
            self._initialize_keyword_search()
            if self.keyword_searcher is None:
                logger.warning("Keyword search not initialized, falling back to vector search")
                self.cache.set(query, vector_results)
                return vector_results

            keyword_scores = self.keyword_searcher.score(query, self.all_chunks)

            final_results = self._reciprocal_rank_fusion(vector_results, keyword_scores)

            self.cache.set(query, final_results)
            return final_results

        except Exception as e:
            logger.error(f"Error in hybrid search, falling back to vector: {e}")
            self.cache.set(query, vector_results)
            return vector_results
