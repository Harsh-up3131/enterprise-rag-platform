"""
FastAPI app factory. Routes stay thin (see app/api/routes/*) — all logic
lives in app/services/*. This file just wires routers together.
"""
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.api.routes import auth, conversations, documents, eval as eval_routes, organizations, query, security
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic in-memory rate limiting for selected API routes."""

    def __init__(self, app, *, limit: int = 60, window_seconds: int = 60, paths: list[str] | None = None):
        super().__init__(app)
        self.limit = limit
        self.window_seconds = max(window_seconds, 1)
        self.paths = paths or []
        self._requests: dict[str, Deque[float]] = defaultdict(deque)

    def _matches_path(self, path: str) -> bool:
        if not self.paths:
            return True
        for pattern in self.paths:
            if path == pattern:
                return True
            if pattern.endswith("/*") and path.startswith(pattern[:-1]):
                return True
            if not pattern.endswith("/*") and path.startswith(pattern.rstrip("/")):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        if self._matches_path(request.url.path):
            client_id = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
            now = time.monotonic()
            bucket = self._requests[client_id]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.limit:
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})

            bucket.append(now)

        return await call_next(request)


app = FastAPI(
    title="Enterprise Knowledge Intelligence Platform (POC)",
    description="Scoped-down MVP of EKIP: permission-aware hybrid RAG with citations, tracing and evaluation.",
    version="0.1.0",
)

cors_origins = settings.cors_allowed_origins or (
    ["http://localhost:5173", "http://localhost:3000"]
    if settings.app_env.lower() != "production"
    else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(
    RateLimitMiddleware,
    limit=60,
    window_seconds=60,
    paths=["/auth/login", "/query"],
)

app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(eval_routes.router)
app.include_router(security.router)


@app.get("/health")
def health():
    return {"status": "ok"}
