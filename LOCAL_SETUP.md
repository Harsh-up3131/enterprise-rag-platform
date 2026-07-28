# Running EKIP on localhost (without Docker)

Step-by-step setup for running the whole stack natively — Postgres, Redis,
Ollama, the FastAPI backend, the Celery worker, and the Vite frontend.

If you'd rather use Docker, see the "Setup instructions" section in
[README.md](README.md) instead.

You will end up with **five things running**: Postgres, Redis, Ollama, the
API (uvicorn), the Celery worker, and the frontend dev server. The last
three each need their own terminal, with the venv activated.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | |
| Node.js 18+ | for the frontend |
| PostgreSQL 14+ | must have the `pgvector` extension available |
| Redis | Celery broker + result backend |
| [Ollama](https://ollama.com) | local LLM, no API key needed |

macOS (Homebrew):

```bash
brew install python@3.11 node postgresql@14 redis pgvector
brew install --cask ollama
```

---

## 2. Start Postgres and Redis

```bash
brew services start postgresql@14
brew services start redis
```

Verify both are up:

```bash
pg_isready            # expect: accepting connections
redis-cli ping        # expect: PONG
```

---

## 3. Create the database

```bash
createuser ekip --createdb
psql postgres -c "ALTER USER ekip WITH PASSWORD 'ekip';"
createdb ekip -O ekip
```

Then enable `pgvector`. This must run as a **superuser**, not as `ekip` —
creating an extension is a privileged operation:

```bash
psql -d ekip -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

> On Homebrew Postgres the superuser is your macOS username, so plain
> `psql -d ekip` already connects as a superuser. There is no `postgres`
> role by default — `psql -U postgres` will fail with
> `role "postgres" does not exist`.

Confirm it worked:

```bash
psql -d ekip -c "\dx"     # 'vector' should be listed
```

---

## 4. Install and start Ollama

```bash
ollama pull llama3.2:3b
ollama serve
```

`ollama serve` listens on `127.0.0.1:11434`. It's often already running as a
background service — if it says the address is in use, it's already up and
you can skip it.

You can swap the model (e.g. `qwen2.5:3b`, `phi3:mini`) via `OLLAMA_MODEL`
in `.env`.

---

## 5. Configure the backend environment

```bash
cp .env.example .env
```

The defaults in `.env.example` are written for **Docker**, so three values
must be changed for local use — the Docker service hostnames (`postgres`,
`redis`, `host.docker.internal`) don't resolve outside Docker:

```ini
DATABASE_URL=postgresql+psycopg://ekip:ekip@localhost:5432/ekip
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434

JWT_SECRET=<any-random-string>
```

Leave the retrieval-tuning and LangSmith values as they are.

---

## 6. Create the venv and install dependencies

From the project root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Confirm you're using the venv's interpreter, not the system one:

```bash
which python      # must print <project>/.venv/bin/python
```

> If `uvicorn` or `celery` later fails with `ModuleNotFoundError` for
> `psycopg`, `app`, or similar, the venv almost certainly isn't active in
> that terminal. Every terminal needs its own `source .venv/bin/activate`.

---

## 7. Initialize the database schema

```bash
python scripts/init_db.py
```

Creates all tables and enables `pgvector`. Optionally seed a demo org, user,
and knowledge base — it prints login credentials you can use immediately:

```bash
python scripts/seed_demo.py
```

---

## 8. Start the backend (terminal 1)

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

`--reload` restarts the server automatically on code changes.

---

## 9. Start the Celery worker (terminal 2)

The worker handles asynchronous document ingestion (parse → chunk → embed).
Uploads will stay stuck in `processing` forever without it.

```bash
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

Two details matter here:

- **`app.workers.celery_app:celery_app`** — the Celery instance is named
  `celery_app` inside `app/workers/celery_app.py`. Passing just
  `-A app.workers` fails with
  `Module 'app.workers' has no attribute 'celery'`.
- **`--pool=solo`** — required on macOS. Celery's default `prefork` pool
  crashes on macOS with `objc[...]: +[NSCharacterSet initialize] may have
  been in progress when fork() was called` followed by
  `WorkerLostError: signal 6 (SIGABRT)`. The alternative is to
  `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` before starting the
  default pool; `--pool=solo` is simpler for local dev and runs tasks in a
  single process.

Also make sure you run this **from the project root** — Celery imports
`app` relative to the current directory, so running it from elsewhere gives
`ModuleNotFoundError: No module named 'app'`.

---

## 10. Start the frontend (terminal 3)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

There is no Vite proxy — the frontend calls the API directly at the origin
in `VITE_API_BASE_URL` (`frontend/src/api.js`), which defaults to
`http://localhost:8000`. If you run the backend on a different port, set
`VITE_API_BASE_URL` in `frontend/.env` to match.

---

## 11. Verify the whole stack

```bash
curl http://localhost:8000/health          # {"status":"ok"}
```

Then in the UI:

1. Sign up (or log in with the `seed_demo.py` credentials).
2. Upload a document and watch its status go
   `processing → ready` — this exercises the Celery worker.
3. Ask a question in the chat and confirm the answer comes back with
   citations.
4. Open the **Security** tab and run the tenant-isolation check — all
   three checks should pass.

> **First run is slow.** The embedding model
> (`sentence-transformers/all-MiniLM-L6-v2`, ~90 MB) downloads from
> huggingface.co the first time a document is ingested or a query runs.
> It needs internet access once, then it's cached locally. If ingestion
> fails immediately with a connection error, this is why.

---

## Starting the project again later

Everything in sections 1-7 is **one-time setup**. Once it's done, you never
need to repeat it — no reinstalling, no recreating the database, and in
particular **do not re-run `scripts/init_db.py` or `scripts/seed_demo.py`**
(the first is unnecessary, the second will create duplicate demo data).

A normal start is just: make sure the three background services are up, then
open three terminals.

### Step 1 — background services

Postgres and Redis are installed as Homebrew services, so they usually
restart automatically after a reboot. Verify rather than assume:

```bash
pg_isready            # expect: accepting connections
redis-cli ping        # expect: PONG
curl -s localhost:11434/api/tags >/dev/null && echo "ollama up"
```

Start whichever isn't running:

```bash
brew services start postgresql@14
brew services start redis
ollama serve                    # only if the curl check above failed
```

### Step 2 — backend (terminal 1)

```bash
cd "$(git rev-parse --show-toplevel)"      # or just cd to the project root
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Step 3 — Celery worker (terminal 2)

```bash
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

### Step 4 — frontend (terminal 3)

```bash
cd frontend
npm run dev
```

No `npm install` needed unless `package.json` changed since last time.

Then open http://localhost:5173.

### Condensed version

If you just want the commands, three terminals from the project root:

```bash
# terminal 1 — API
source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# terminal 2 — ingestion worker
source .venv/bin/activate && celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo

# terminal 3 — frontend
cd frontend && npm run dev
```

### Shutting down

`Ctrl+C` in each of the three terminals. The background services can be left
running; to stop them explicitly:

```bash
brew services stop postgresql@14
brew services stop redis
```

### When you *do* need to re-run setup steps

| What changed | What to re-run |
|---|---|
| `requirements.txt` | `pip install -r requirements.txt` |
| `frontend/package.json` | `cd frontend && npm install` |
| A model added in `app/models/` | `python scripts/init_db.py` (creates new tables only) |
| `.env` values | restart uvicorn and the Celery worker — config is read at startup |
| Switched Ollama model | `ollama pull <model>`, update `OLLAMA_MODEL`, restart the API |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'psycopg'`**
The venv isn't active in that terminal — the traceback will show paths under
`/opt/homebrew/lib/python3.11/site-packages` instead of `.venv`. Run
`source .venv/bin/activate`, then confirm with `which python`.

**`permission denied to create extension "vector"` / `Must be superuser`**
You're connected as `ekip`, which isn't a superuser. Run the
`CREATE EXTENSION` as your own (superuser) account: `psql -d ekip -c "..."`.

**`role "postgres" does not exist`**
Homebrew Postgres doesn't create a `postgres` role. Drop `-U postgres` and
connect as yourself.

**`could not open extension control file .../vector.control`**
pgvector isn't installed for your Postgres version. `brew install pgvector`,
then retry `CREATE EXTENSION`. If it's still missing, build it against your
specific installation:

```bash
export PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config
git clone https://github.com/pgvector/pgvector.git
cd pgvector && make && make install
```

**`Unable to load celery application ... has no attribute 'celery'`**
Use the full path to the instance:
`-A app.workers.celery_app:celery_app`.

**`ModuleNotFoundError: No module named 'app'` (Celery)**
Run the command from the project root, not from a subdirectory.

**`WorkerLostError: signal 6 (SIGABRT)` / `NSCharacterSet initialize ... fork()`**
macOS fork-safety issue with Celery's prefork pool. Add `--pool=solo`.

**CORS error: `No 'Access-Control-Allow-Origin' header is present`**
Usually a red herring. `app/main.py` already allows all origins, but FastAPI
does not attach CORS headers to unhandled `500` responses, so a server-side
crash surfaces in the browser as a CORS error. Check the uvicorn terminal
for the real traceback — a common cause is forgetting to run
`scripts/init_db.py`, so the tables don't exist yet.

**Uploads stay in `processing` forever**
The Celery worker isn't running, or it can't reach Redis. Check terminal 2
and confirm `redis-cli ping` returns `PONG`.

**Ollama connection refused**
Confirm `ollama serve` is running and that `OLLAMA_BASE_URL` is
`http://localhost:11434` — not the Docker-oriented
`http://host.docker.internal:11434`.
