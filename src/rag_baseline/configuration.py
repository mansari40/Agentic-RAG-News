from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    mediastack_api_key: str
    openai_api_key: str
    postgres_url: str
    qdrant_url: str

    qdrant_collection_name: str = "news_chunks"
    embedding_model_name: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = ApplicationSettings()  # type: ignore[call-arg]
