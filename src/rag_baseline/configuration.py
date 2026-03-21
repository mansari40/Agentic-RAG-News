from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    mediastack_api_key: str | None = None
    openai_api_key: str | None = None
    postgres_url: str | None = None
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "news_chunks"
    embedding_model_name: str = "text-embedding-3-small"
    chat_model_name: str = "gpt-4o-mini"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings: ApplicationSettings = ApplicationSettings()
