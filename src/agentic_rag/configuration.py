"""
Settings for the Agentic RAG pipeline.

Covers API keys, model names, retrieval limits, and cost tracking.
Relevance decisions are made by the LLM — not by thresholds or scoring math here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgenticRAGSettings(BaseSettings):
    # API Keys
    openai_api_key: str | None = None
    mediastack_api_key: str | None = None
    tavily_api_key: str | None = None
    langchain_api_key: str | None = None

    # Model Config
    chat_model_name: str = "gpt-4o-mini"
    verifier_model_name: str = "gpt-4o"
    researcher_model_name: str = "gpt-4o"
    ranker_model_name: str = "gpt-4o-mini"
    embedding_model_name: str = "text-embedding-3-small"
    conversational_temperature: float = 0.7
    synthesis_temperature: float = 0.2
    reflection_temperature: float = 0.0

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_project: str = "Agentic News RAG"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # Date cutoffs — sources older than min_allowed_evidence_date are always dropped
    min_allowed_evidence_date: str = "2026-01-01"
    news_fetch_days_back: int = 30  # look back this many days for news queries
    general_fetch_days_back: int = 90  # look back this many days for general queries
    news_query_days_back: int = 30  # alias used by older code paths
    mediastack_days_back: int = 30
    min_source_quality: float = 0.35

    # How many results each tool can return
    mediastack_max_results: int = 25
    tavily_max_results: int = 10
    tavily_search_depth: str = "advanced"
    baseline_top_k: int = 5
    max_sources_to_rank: int = 50  # cap on how many sources go into the ranker
    max_sources_to_verify: int = 20  # how many the verifier actually reads
    ranker_top_n: int = 20  # how many the ranker passes to the verifier
    max_sources_to_synthesize: int = 8  # how many sources the synthesizer uses

    # How many steps the researcher can take
    max_researcher_steps: int = 6

    # Pipeline loop limits
    max_retrieval_iterations: int = 2
    max_refinement_iterations: int = 1  # max times we loop back for a second research pass
    weak_result_threshold: int = (
        3  # if a tool returns fewer than this, nudge the LLM to reformulate
    )
    enable_memory: bool = True
    max_conversation_history: int = 10
    cache_ttl_minutes: int = 60
    enable_query_cache: bool = True

    # Token Limits
    max_synthesis_tokens: int = 1200
    max_content_chars_per_source: int = 600

    # Token prices used for cost tracking
    openai_input_cost_per_token: float = 0.00000015  # gpt-4o-mini input
    openai_output_cost_per_token: float = 0.0000006  # gpt-4o-mini output
    researcher_input_cost_per_token: float = 0.0000025  # gpt-4o input
    researcher_output_cost_per_token: float = 0.000010  # gpt-4o output
    verifier_input_cost_per_token: float = 0.0000025  # gpt-4o input
    verifier_output_cost_per_token: float = 0.000010  # gpt-4o output

    log_level: str = "INFO"

    mediastack_countries: str = "de"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


agentic_settings = AgenticRAGSettings()
