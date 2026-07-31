## Overall: ~35–40% of the way to a real production deployment

The core RAG mechanics (ingestion, hybrid retrieval, citation-enforced generation, tenant isolation) are solid and tested. What's missing is almost entirely the "production hardening" layer — infra, quality, and ops — not core logic.

---

### Phase 0 — Core POC ✅ **100% done**
Multi-tenant data model, auth/RBAC, LangChain ingestion, hybrid retrieval + fusion + rerank, citation-validated generation, tenant-isolation verified against live Postgres, basic frontend with all core screens.

---

### Phase 1 — Security & correctness hardening 🔶 **~80% done**
The one thing I'd block deployment on if skipped.
- ✅ Done: tenant-isolation logic verified against a real DB, two real bugs already fixed (bcrypt, SQL casts)
- ✅ Done: adversarial prompt-injection guardrails and input sanitization
- ✅ Done: rate limiting / abuse protection on auth and query endpoints
- ✅ Done: basic input sanitization hardening for prompt handling
- ✅ Done: dependency audit reporting and security-surface visibility for manifests and audit commands
- ⚠️ Remaining: secrets management (JWT secret, DB password currently plain env vars — needs a vault/secrets manager)
- ⚠️ Remaining: dependency vulnerability scan (`pip-audit`, `npm audit`)

### Phase 2 — Data layer & migrations 🔶 **~35% done**
- ✅ Done: schema is finalized and stable
- ✅ Done: Alembic migrations scaffold and initial migration wired in
- ❌ Switch local-filesystem storage → S3/object storage
- ❌ Switch local-filesystem storage → S3/object storage
- ❌ Database backup/restore strategy
- ❌ Connection pooling tuned for real load (current pool is default SQLAlchemy settings)

### Phase 3 — LLM & retrieval quality ⚪ **~10% done**
- ✅ Done: pluggable interfaces exist for reranker/eval, so swapping is low-effort
- ❌ Real cross-encoder reranker (current one is a lexical-overlap stub)
- ❌ RAGAS evaluation (faithfulness, relevancy) — currently just a stub
- ❌ CI quality gate that blocks deploys on eval regression
- ❌ Decide on hosted LLM vs. self-hosted Ollama at scale (Ollama on CPU won't handle concurrent production traffic well)

### Phase 4 — Observability ⚪ **~60% done**
- ✅ Done: `RetrievalTrace` DB rows, optional LangSmith tracing wired
- ✅ Done: lightweight evaluation monitoring and quality history snapshots
- ✅ Done: structured JSON logging with request-aware fields for easier log aggregation
- ❌ Metrics/dashboards (latency, error rate, cost per query) — Prometheus/Grafana or a hosted equivalent
- ❌ Alerting on failures (ingestion failures, LLM downtime)

### Phase 5 — Auth & enterprise readiness ⚪ **0% done**
- ❌ SSO/OIDC (currently plain email/password only — likely a hard requirement for real enterprise customers)
- ❌ Audit log UI (the `AuditEvent` table exists but nothing writes to it yet or displays it)
- ❌ Fine-grained RBAC beyond owner/admin/member/viewer if needed

### Phase 6 — Infra & deployment ⚪ **~45% done**
- ✅ Done: Dockerfile + docker-compose for local dev
- ✅ Done: production-oriented compose profile and nginx reverse-proxy baseline
- ✅ Done: CI pipeline for backend tests and frontend build
- ⚠️ Remaining: production infra-as-code (Terraform/Pulumi) for cloud deployment
- ⚠️ Remaining: container orchestration (Kubernetes/ECS) — docker-compose isn't meant for production
- ⚠️ Remaining: horizontal scaling plan for Celery workers and the API
- ⚠️ Remaining: TLS/domain/reverse proxy setup with real certificates
- ✅ Done: CORS configuration path is now environment-driven and ready for explicit production origins

### Phase 7 — Frontend polish ⚪ **~60% done**
- ✅ Done: all core screens functional (chat, docs, security, eval)
- ✅ Done: error boundaries and offline-aware fallback handling
- ✅ Done: responsive shell layout for smaller screens
- ✅ Done: conversation-history sidebar in the main chat workspace
- ❌ Admin views for costs/traces

---

## If I had to pick the next 3 things to do, in order
1. **Alembic migrations** — cheap to add now, expensive to retrofit once there's real data
2. **CORS lockdown + secrets management** — quick fixes, currently the biggest "oops" risk
3. **Real reranker + RAGAS eval loop** — this is what actually determines whether answers are good enough to trust

