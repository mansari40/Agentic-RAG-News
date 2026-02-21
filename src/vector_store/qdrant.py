from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    ScoredPoint,
    VectorParams,
)
from rag_baseline.configuration import settings


class QdrantRepository:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            timeout=120,
        )

    def create_collection_if_not_exists(self, vector_size: int) -> None:
        collections = self.client.get_collections().collections
        existing_names = [collection.name for collection in collections]

        if settings.qdrant_collection_name not in existing_names:
            self.client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, and payloads must have equal length")

        points = [
            PointStruct(
                id=ids[index],
                vector=vectors[index],
                payload=payloads[index],
            )
            for index in range(len(ids))
        ]

        self.client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int,
    ) -> list[ScoredPoint]:
        response = self.client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            limit=top_k,
        )

        return response.points
