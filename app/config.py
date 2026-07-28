"""
Centralized application configuration.

Everything the system needs to know about its environment lives here,
loaded once from env vars / .env. Nothing else in the codebase should call
os.environ directly — this keeps config auditable and testable.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql+psycopg://ekip:ekip@localhost:5432/ekip"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth ---
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

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

    # --- Chunking (target size; the version string itself lives in chunker.py) ---
    chunk_target_tokens: int = 300
    chunk_overlap_tokens: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
