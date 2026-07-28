"""
FastAPI app factory. Routes stay thin (see app/api/routes/*) — all logic
lives in app/services/*. This file just wires routers together.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, organizations, documents, query, eval as eval_routes, security

app = FastAPI(
    title="Enterprise Knowledge Intelligence Platform (POC)",
    description="Scoped-down MVP of EKIP: permission-aware hybrid RAG with citations, tracing and evaluation.",
    version="0.1.0",
)

# NOTE(POC): wide open for local dev convenience. In production, restrict
# allow_origins to the actual frontend origin(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
