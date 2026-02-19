import logging

from openai import OpenAI, OpenAIError
from rag_baseline.configuration import settings
from rag_baseline.custom_exceptions import EmbeddingError
from rag_baseline.utils.retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)

    @retry_with_backoff(  # type: ignore[misc]
        max_retries=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions=(OpenAIError, ConnectionError, TimeoutError),
    )
    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for text with retry logic.

        Raises:
            EmbeddingError: If embedding generation fails after retries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, using default")
            return [0.0] * 1536

        try:
            response = self.client.embeddings.create(
                model=settings.embedding_model_name,
                input=text[:8000],
            )
            return response.data[0].embedding

        except OpenAIError as e:
            logger.error(f"OpenAI API error during embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}") from e
