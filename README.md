# EKIP — Enterprise Knowledge Intelligence Platform (MVP / POC)

This is a **scoped-down MVP** of the full EKIP blueprint. The goal of this
codebase is to prove out the *shape* of every major subsystem described in
the foundation doc — tenancy, permission-aware ingestion, hybrid retrieval,
citation-enforced generation, tracing, and evaluation — with minimal,
readable, modular code. It intentionally does **not** implement production
concerns yet (retries, real OCR, real reranker models, real auth provider,
CI eval gates, observability backends). Those are called out as `# TODO(prod)`
comments throughout the code so the next phase is obvious.

## What's implemented in this POC

- Multi-tenant data model (Organization → KnowledgeBase → Document →
  DocumentVersion → Chunk) with `organization_id` on every tenant table.
- Simple JWT auth + membership/role model (RBAC skeleton).
- Document upload → async ingestion pipeline (Celery + Redis) →
  parse (LangChain loaders for PDF/TXT/MD) → chunk (LangChain
  `RecursiveCharacterTextSplitter`, heading-aware) → embed → store
  (Postgres + pgvector).
- Document-level ACLs enforced **before** retrieval (not post-filtered).
- Hybrid retrieval: Postgres full-text (lexical) + pgvector (dense),
  combined with Reciprocal Rank Fusion (RRF).
- A pluggable reranker interface with a simple cross-encoder-style stub.
- Grounded generation: evidence pack → prompt → local LLM (Ollama) →
  citation extraction/validation → abstention if evidence is weak.
- A `RetrievalTrace` row persisted per query (query, scores, chosen
  chunks, latency), plus optional **LangSmith** tracing on the same calls
  (`@traceable` on `retrieve()`, `generate()`, `answer_question()`) — off
  by default, on if you set `LANGCHAIN_API_KEY`.
- A tiny deterministic evaluation harness (Recall@K, citation validity)
  you can run against a hand-written eval set.
- **Automated tenant-isolation self-check** (`app/services/security/tenant_isolation_check.py`):
  plants a document in a throwaway second organization and confirms it
  cannot be retrieved from the calling org, plus confirms a document with
  no ACL rows is invisible to everyone. Runnable via the API, the
  frontend's Security tab, or as a pytest integration test.
- A full frontend (see `frontend/`) — chat with citations, document
  upload/delete with progress, and the Security tab above.

## What's stubbed / explicitly out of scope for this pass

- Real OCR, PPTX/XLSX ingestion, table-structure extraction.
- Real reranker model / RAGAS / OpenTelemetry wiring (interfaces exist,
  real integrations are `TODO(prod)`). LangSmith tracing is wired in for
  real, but optional.
- Enterprise SSO — plain email/password JWT only.
- CI quality gates, Terraform, multi-provider LLM abstraction (one
  provider wired: Ollama, running locally, no API key needed).

## Architecture (this POC)

```
Client
  │
FastAPI (app/main.py)
  │
  ├── /auth            → app/api/routes/auth.py
  ├── /organizations    → app/api/routes/organizations.py
  ├── /documents         → app/api/routes/documents.py  (upload → Celery task)
  ├── /query              → app/api/routes/query.py       (retrieval + generation)
  └── /eval                 → app/api/routes/eval.py       (run eval set)

Celery worker (app/workers/tasks.py)
  → services/ingestion/pipeline.py
      parser.py → chunker.py → embedder.py → DB (chunks + embedding)

services/retrieval/retriever.py
  lexical.py (Postgres tsvector) + dense.py (pgvector cosine) → fusion.py (RRF) → reranker.py

services/generation/
  prompt.py (evidence pack builder) → llm_client.py → citation_validator.py → guardrails.py
```

## Directory layout

```
ekip/
  app/
    main.py                  FastAPI app factory, router wiring
    config.py                Pydantic settings (env-driven)
    database.py               SQLAlchemy engine/session
    models/                   ORM models (one file per aggregate)
    schemas/                  Pydantic request/response models
    core/
      security.py             password hashing, JWT
      deps.py                  current_user / current_org / RBAC deps
    api/routes/                FastAPI routers (thin — call services)
      security.py                admin/security routes (isolation check)
    services/
      ingestion/               parse (LangChain loaders), chunk (LangChain
                                  splitter), embed, pipeline orchestrator
      retrieval/                lexical, dense, fusion, reranker, retriever
      generation/                prompt, llm_client, citation_validator, guardrails
      evaluation/                 deterministic metrics + a RAGAS-shaped stub
      security/                    tenant_isolation_check.py
    workers/                    celery app + tasks
    utils/                      logging helper
  scripts/
    init_db.py                 create tables + pgvector extension
    seed_demo.py                create a demo org/user/kb for local testing
  tests/
    test_retrieval.py           unit smoke tests (no DB needed)
    test_tenant_isolation.py     integration test (needs live Postgres+pgvector)
  frontend/                    React + Vite UI (see frontend/README.md)
  docker-compose.yml            postgres(pgvector) + redis + api + worker
  requirements.txt
  .env.example
```

## Setup instructions

> Running natively instead of in Docker? See **[LOCAL_SETUP.md](LOCAL_SETUP.md)**
> for a full localhost walkthrough (venv, Postgres/pgvector, Redis, uvicorn
> `--reload`, Celery, frontend) plus a troubleshooting section.

### 1. Prerequisites
- Docker + Docker Compose
- [Ollama](https://ollama.com) installed and running on your host machine
  (not in Docker — the backend connects to it over `host.docker.internal`)
- (optional, for running outside Docker) Python 3.11+

### 2. Pull a local model and start Ollama
```bash
ollama pull llama3.2:3b   # small, fast, good enough for a POC
ollama serve               # usually already running as a background service
```
You can swap in any other Ollama model (e.g. `qwen2.5:3b`, `phi3:mini`) by
setting `OLLAMA_MODEL` in `.env`.

### 3. Configure environment
```bash
cp .env.example .env
# defaults already point at Ollama on your host — no API key needed
```

### 4. Run everything with Docker Compose
```bash
docker compose up --build
```
This starts:
- `postgres` — Postgres 16 with the `pgvector` extension (via `pgvector/pgvector` image)
- `redis` — broker/result backend for Celery
- `api` — FastAPI app on `http://localhost:8000` (docs at `/docs`)
- `worker` — Celery worker consuming ingestion jobs

> **Note:** the embedding model (`sentence-transformers/all-MiniLM-L6-v2`)
> downloads from huggingface.co the first time a document is ingested or a
> query is run — needs internet access once, then it's cached locally.
> If ingestion fails immediately with a connection error, this is why.

### 5. Initialize the database (first run only)
```bash
docker compose exec api python scripts/init_db.py
docker compose exec api python scripts/seed_demo.py
```
`seed_demo.py` prints a demo user's email/password and an org id you can
use to log in via `/auth/login`.

### 6. Try the flow
1. `POST /auth/login` → get a JWT.
2. `POST /documents/upload` (multipart, with the JWT) → creates a
   `Document` + `DocumentVersion`, queues an ingestion job.
3. Poll `GET /documents/{id}` until `status == "ready"` (or watch the
   `ingestion_status` field for finer-grained progress: pending → parsing
   → chunking → embedding → ready).
4. `POST /query` with `{"question": "..."}` → retrieval + grounded answer
   with citations + a `trace_id`.
5. `POST /eval/run` → runs the sample evaluation set in
   `services/evaluation/sample_eval_set.json` and returns aggregate metrics.
6. `POST /admin/security/isolation-check` (owner/admin only) → runs the
   tenant-isolation self-check and returns pass/fail per check. Also
   available from the frontend's **Security** tab, and as a pytest
   integration test (`tests/test_tenant_isolation.py`) for CI.

### 7. Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open `http://localhost:5173`. See `frontend/README.md` for details.

### 8. Optional: LangSmith tracing
Off by default. To turn it on, get a free API key at
https://smith.langchain.com, then in `.env`:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your_key
LANGCHAIN_PROJECT=ekip
```
No code changes needed — `retrieve()`, `generate()`, and `answer_question()`
are already decorated with `@traceable` and will start reporting nested
traces to your LangSmith project.

### 9. Running locally without Docker
Note: without Docker, point `OLLAMA_BASE_URL` in `.env` at `http://localhost:11434` instead of `http://host.docker.internal:11434`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs)   # or use python-dotenv
uvicorn app.main:app --reload
# in another shell:
celery -A app.workers.celery_app worker --loglevel=info
```
You'll need a local Postgres with `CREATE EXTENSION vector;` and a local Redis.

## Next steps toward production (see original blueprint)
- Swap the embedding/reranker stubs for real hosted models.
- Add Alembic migrations instead of `create_all`.
- Add Langfuse/OpenTelemetry tracing around each pipeline stage.
- Add RAGAS-based generation evaluation + CI quality gate.
- Add prompt-injection/guardrail test suite for adversarial documents.
- Add tenant-isolation adversarial tests.
- Build out the Next.js frontend (chat UI, doc admin, evidence viewer).
