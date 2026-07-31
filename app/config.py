"""
Centralized application configuration.

Everything the system needs to know about its environment lives here,
loaded once from env vars / .env. Nothing else in the codebase should call
os.environ directly — this keeps config auditable and testable.
"""
import os
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Environment ---
    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV"))

    # --- Database ---
    database_url: str = "postgresql+psycopg://ekip:ekip@localhost:5432/ekip"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth ---
    jwt_secret: str | None = Field(default=None, validation_alias=AliasChoices("JWT_SECRET"))
    jwt_secret_file: str | None = Field(default=None, validation_alias=AliasChoices("JWT_SECRET_FILE"))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- CORS ---
    cors_allowed_origins: list[str] | str = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS"),
    )

    # --- LLM (local, via Ollama — no API key needed) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    # NOTE(POC): using a small local sentence-transformers model so the demo
    # runs without extra hosted-embedding credentials. Swap for a hosted
    # embedding API in production for quality/scale.
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # --- Retrieval tuning (versioned "retriever_config") ---
    retriever_config_version: str = "v1-rrf-lexical-dense"
    lexical_top_k: int = 20
    dense_top_k: int = 20
    fusion_top_k: int = 10
    rerank_top_k: int = 5
    rrf_k: int = 60  # standard RRF smoothing constant
    min_evidence_score: float = 0.15  # below this -> abstain

    # --- LangSmith tracing ---
    langsmith_tracing: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"),
    )
    langsmith_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
    )
    langsmith_project: str = Field(
        default="default",
        validation_alias=AliasChoices("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
    )

    # --- Chunking (target size; the version string itself lives in chunker.py) ---
    chunk_target_tokens: int = 300
    chunk_overlap_tokens: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.jwt_secret_file:
            secret_path = Path(self.jwt_secret_file)
            if secret_path.exists():
                self.jwt_secret = secret_path.read_text(encoding="utf-8").strip()

        if not self.jwt_secret:
            self.jwt_secret = "dev-secret-change-me" if self.app_env.lower() != "production" else None

        if self.app_env.lower() == "production":
            if not self.jwt_secret:
                raise ValueError("JWT_SECRET or JWT_SECRET_FILE must be set when APP_ENV=production")
            if not self.cors_allowed_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must be set when APP_ENV=production")

        return self

    def model_post_init(self, __context) -> None:
        """Keep LangSmith SDK environment variables in sync with the app config."""
        os.environ["LANGSMITH_TRACING"] = str(self.langsmith_tracing).lower()
        if self.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project


settings = Settings()
