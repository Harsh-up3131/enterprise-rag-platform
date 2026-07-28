"""
Embedding stage: chunk text -> dense vector.

POC scope: a small local sentence-transformers model so the whole system
runs without extra hosted-embedding credentials/latency. The model is
loaded once per process (module-level singleton) since load time is
non-trivial. Swap `EMBEDDING_MODEL_VERSION` + this module for a hosted
embedding API in production; nothing else in the codebase needs to change
since retrieval only depends on `embed_text`/`embed_texts`.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings

EMBEDDING_MODEL_VERSION = settings.embedding_model_name


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
