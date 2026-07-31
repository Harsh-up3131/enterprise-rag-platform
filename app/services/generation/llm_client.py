"""
LLM provider client.

POC scope: a single provider (Ollama, running locally) behind a tiny
function interface so a hosted provider can be swapped in later without
touching anything upstream (prompt.py, query_service.py). No API key
needed — Ollama serves models locally over HTTP.
"""
import requests
from langsmith import traceable

from app.config import settings


@traceable(name="llm_generate", run_type="llm")
def generate(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.0,
) -> str:
    # Temperature defaults to 0: grounded answers should be reproducible, and
    # sampling was the main source of the model silently dropping its
    # [chunk_id] citation tags (which the pipeline treats as an abstention).
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        # Lets the rest of the pipeline (retrieval, citation validation, tracing)
        # be exercised/tested even if Ollama isn't running yet.
        return (
            f"[Local LLM not reachable at {settings.ollama_base_url}. "
            f"Make sure Ollama is running and you've pulled '{settings.ollama_model}'.]"
        )

