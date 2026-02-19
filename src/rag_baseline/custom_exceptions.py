class RAGBaseException(Exception):
    """Base exception for all RAG system errors"""

    pass


class StorageLayerError(RAGBaseException):
    """Database operations failed"""

    pass


class ExternalAPIError(RAGBaseException):
    """External API calls failed (OpenAI, MediaStack, etc.)"""

    pass


class VectorStoreError(RAGBaseException):
    """Qdrant vector store operations failed"""

    pass


class EmbeddingError(RAGBaseException):
    """Text embedding generation failed"""

    pass


class RetrievalError(RAGBaseException):
    """Document retrieval failed"""

    pass


class GenerationError(RAGBaseException):
    """Answer generation failed"""

    pass


class IngestionError(RAGBaseException):
    """Article ingestion pipeline failed"""

    pass
