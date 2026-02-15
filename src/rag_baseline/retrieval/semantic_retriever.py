from rag_baseline.configuration import settings
from rag_baseline.domain_models import RetrievalResult
from rag_baseline.embedding.text_embedder import EmbeddingService
from rag_baseline.retrieval.retrieval_cache import RetrievalCache
from vector_store.qdrant import QdrantRepository


class SemanticRetriever:
    def __init__(self) -> None:
        self.embedding_generator: EmbeddingService = EmbeddingService()
        self.vector_store: QdrantRepository = QdrantRepository()
        self.cache: RetrievalCache = RetrievalCache()

    def retrieve(self, query: str) -> list[RetrievalResult]:
        cached: list[RetrievalResult] | None = self.cache.get(query)
        if cached is not None:
            return cached

        query_embedding = self.embedding_generator.embed(query)

        search_results = self.vector_store.search(
            query_embedding,
            settings.top_k_results,
        )

        results: list[RetrievalResult] = []

        for point in search_results:
            results.append(
                RetrievalResult(
                    chunk_id=str(point.id),
                    article_id=str(point.payload["article_id"]),
                    content=str(point.payload["content"]),
                    similarity_score=float(point.score),
                )
            )

        self.cache.set(query, results)

        return results
