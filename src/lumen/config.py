"""Validated environment and defaults for Lumen (pydantic-settings)."""

from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from environment and optional `.env` file in project root."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — OpenAI SDK; point OPENAI_BASE_URL at OpenRouter for freemium use
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "LUMEN_OPENAI_BASE_URL"),
    )
    lumen_chat_model: str = Field(default="openrouter/auto:free", validation_alias="LUMEN_CHAT_MODEL")
    lumen_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="LUMEN_EMBEDDING_MODEL",
    )
    lumen_use_mock_embeddings: bool = Field(
        default=False,
        validation_alias="LUMEN_USE_MOCK_EMBEDDINGS",
    )

    # Search
    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")
    serper_api_key: str | None = Field(default=None, validation_alias="SERPER_API_KEY")

    # Chroma
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        validation_alias="CHROMA_PERSIST_DIRECTORY",
    )
    chroma_collection_prefix: str = Field(
        default="lumen_session",
        validation_alias="CHROMA_COLLECTION_PREFIX",
    )

    # HTTP fetch
    lumen_http_user_agent: str = Field(
        default="LumenResearchBot/0.1",
        validation_alias="LUMEN_HTTP_USER_AGENT",
    )
    lumen_fetch_max_concurrency: int = Field(
        default=4,
        validation_alias="LUMEN_FETCH_MAX_CONCURRENCY",
    )
    lumen_fetch_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="LUMEN_FETCH_TIMEOUT_SECONDS",
    )

    # Observability
    langchain_tracing_v2: bool = Field(default=False, validation_alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str | None = Field(default=None, validation_alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="lumen", validation_alias="LANGCHAIN_PROJECT")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias="LANGCHAIN_ENDPOINT",
    )
    lumen_log_level: str = Field(default="INFO", validation_alias="LUMEN_LOG_LEVEL")

    # App
    lumen_secret_key: str | None = Field(default=None, validation_alias="LUMEN_SECRET_KEY")
    lumen_public_url: str | None = Field(default=None, validation_alias="LUMEN_PUBLIC_URL")
    lumen_host: str = Field(default="127.0.0.1", validation_alias="LUMEN_HOST")
    lumen_port: int = Field(default=8000, validation_alias="LUMEN_PORT")

    # Guards
    lumen_max_output_tokens: int = Field(default=4096, validation_alias="LUMEN_MAX_OUTPUT_TOKENS")
    lumen_max_retrieval_chunks: int = Field(default=24, validation_alias="LUMEN_MAX_RETRIEVAL_CHUNKS")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for import-time use in workers."""
    return Settings()
