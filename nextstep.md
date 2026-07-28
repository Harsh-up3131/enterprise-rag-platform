## Overall: ~35–40% of the way to a real production deployment

The core RAG mechanics (ingestion, hybrid retrieval, citation-enforced generation, tenant isolation) are solid and tested. What's missing is almost entirely the "production hardening" layer — infra, quality, and ops — not core logic.

---

### Phase 0 — Core POC ✅ **100% done**
Multi-tenant data model, auth/RBAC, LangChain ingestion, hybrid retrieval + fusion + rerank, citation-validated generation, tenant-isolation verified against live Postgres, basic frontend with all core screens.

---

### Phase 1 — Security & correctness hardening 🔶 **~25% done**
The one thing I'd block deployment on if skipped.
- ✅ Done: tenant-isolation logic verified against a real DB, two real bugs already fixed (bcrypt, SQL casts)
- ❌ Adversarial prompt-injection test suite (malicious document content trying to hijack the LLM)
- ❌ Rate limiting / abuse protection on auth and query endpoints
- ❌ Input sanitization audit (file upload MIME sniffing, not just extension checks)
- ❌ Secrets management (JWT secret, DB password currently plain env vars — needs a vault/secrets manager)
- ❌ Dependency vulnerability scan (`pip-audit`, `npm audit`)

### Phase 2 — Data layer & migrations 🔶 **~15% done**
- ✅ Done: schema is finalized and stable
- ❌ Alembic migrations (currently `create_all` — any schema change means manual intervention or data loss)
- ❌ Switch local-filesystem storage → S3/object storage
- ❌ Database backup/restore strategy
- ❌ Connection pooling tuned for real load (current pool is default SQLAlchemy settings)

### Phase 3 — LLM & retrieval quality ⚪ **~10% done**
- ✅ Done: pluggable interfaces exist for reranker/eval, so swapping is low-effort
- ❌ Real cross-encoder reranker (current one is a lexical-overlap stub)
- ❌ RAGAS evaluation (faithfulness, relevancy) — currently just a stub
- ❌ CI quality gate that blocks deploys on eval regression
- ❌ Decide on hosted LLM vs. self-hosted Ollama at scale (Ollama on CPU won't handle concurrent production traffic well)

### Phase 4 — Observability ⚪ **~20% done**
- ✅ Done: `RetrievalTrace` DB rows, optional LangSmith tracing wired
- ❌ Structured logging (JSON logs, not print-style)
- ❌ Metrics/dashboards (latency, error rate, cost per query) — Prometheus/Grafana or a hosted equivalent
- ❌ Alerting on failures (ingestion failures, LLM downtime)

### Phase 5 — Auth & enterprise readiness ⚪ **0% done**
- ❌ SSO/OIDC (currently plain email/password only — likely a hard requirement for real enterprise customers)
- ❌ Audit log UI (the `AuditEvent` table exists but nothing writes to it yet or displays it)
- ❌ Fine-grained RBAC beyond owner/admin/member/viewer if needed

### Phase 6 — Infra & deployment ⚪ **~10% done**
- ✅ Done: Dockerfile + docker-compose for local dev
- ❌ Production infra-as-code (Terraform/Pulumi) for cloud deployment
- ❌ Container orchestration (Kubernetes/ECS) — docker-compose isn't meant for production
- ❌ CI/CD pipeline (build, test, deploy on merge)
- ❌ Horizontal scaling plan for Celery workers and the API
- ❌ TLS/domain/reverse proxy setup
- ❌ CORS locked down to real frontend origin (currently wide open `*`)

### Phase 7 — Frontend polish ⚪ **~15% done**
- ✅ Done: all core screens functional (chat, docs, security, eval)
- ❌ Error boundaries / offline handling
- ❌ Mobile responsiveness
- ❌ Conversation history sidebar (currently conversations aren't listed/resumable)
- ❌ Admin views for costs/traces

---

## If I had to pick the next 3 things to do, in order
1. **Alembic migrations** — cheap to add now, expensive to retrofit once there's real data
2. **CORS lockdown + secrets management** — quick fixes, currently the biggest "oops" risk
3. **Real reranker + RAGAS eval loop** — this is what actually determines whether answers are good enough to trust

