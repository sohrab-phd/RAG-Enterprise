# First Run (Version 1.0.0)

Canonical bring-up guide for RAG-enterprise **Version 1.0.0** from a fresh clone.
Follow the sections **in order**. Commands assume you start each package section from
the directory named in that step.

This path uses:

- Local Docker Compose for PostgreSQL (pgvector) and Redis
- Backend defaults suitable for a first demo: `LLM_BACKEND=echo`,
  `EMBEDDING_BACKEND=deterministic` (no external model API keys required)
- The operator console for Knowledge, Chat, and Evaluation

---

## Prerequisites

Install and verify the following on your machine.

| Software | Recommended version | Notes |
| --- | --- | --- |
| Git | Any recent release | Clone and worktree |
| Docker Desktop | Current stable | Or Docker Engine **with Compose v2** |
| Python | **3.12+** | Required by `backend/pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Current stable | Backend package manager |
| Node.js | **20+** | Frontend runtime |
| npm | Bundled with Node | Frontend installs |

Verify:

```bash
git --version
docker --version
docker compose version
python --version
uv --version
node --version
npm --version
```

Expected: each command prints a version; Python reports 3.12 or newer; Node reports
20 or newer; `docker compose version` succeeds (Compose v2).

---

## Clone repository

```bash
git clone https://github.com/sohrab-phd/RAG-Enterprise.git
cd RAG-Enterprise
```

Open the cloned directory in your editor or terminal. All later paths are relative to
this repository root unless a step says otherwise (`backend/`, `frontend/`).

---

## Environment

Copy the example environment file at the **repository root** (used by Docker Compose):

```bash
# macOS / Linux / Git Bash
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

Also copy the same file into `backend/` so the API process loads matching settings
when you run commands from `backend/` (the backend reads `.env` from its working
directory):

```bash
# macOS / Linux / Git Bash
cp .env.example backend/.env
```

```powershell
# Windows PowerShell
Copy-Item .env.example backend/.env
```

Do **not** commit `.env` files (they are gitignored).

### Important Version 1.0.0 variables

Only the values that matter for a standard local first run are listed. Defaults from
`.env.example` are enough unless you change ports or passwords.

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment (`development` for local work). |
| `APP_DEBUG` | Enables debug-oriented app behavior when `true`. |
| `LOG_LEVEL` | Structured log verbosity (`INFO` is fine to start). |
| `BACKEND_HOST` / `BACKEND_PORT` | Bind address and port for the API (default `0.0.0.0:8000`). |
| `API_V1_PREFIX` | API mount path (must stay `/api/v1` for the console). |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Database host/port as seen from your host machine (`localhost:5432`). |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credentials Compose uses to create the database. |
| `DATABASE_URL` | Async SQLAlchemy URL the backend uses (`postgresql+asyncpg://…`). Must match Postgres credentials. |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_URL` | Local Redis from Compose (present for local stack completeness). |
| `FILE_STORAGE_ROOT` | Local folder for uploaded binaries (default `storage/uploads`; created at startup). |
| `VITE_API_BASE_URL` | Frontend → backend base URL (default `http://localhost:8000`). |

### Recommended local additions (optional)

You may add these to `backend/.env` for a smoother first Chat experience with the
default **deterministic** embeddings (not semantic):

```bash
LLM_BACKEND=echo
EMBEDDING_BACKEND=deterministic
GENERATION_MIN_EVIDENCE_SCORE=0.0
```

Without lowering the evidence score, Chat may abstain more often under deterministic
embeddings. `echo` and `deterministic` are the backend defaults and do **not** need
API keys.

Frontend actor headers default in code to the development stub IDs (no login in
Version 1.0.0). Override only if you intentionally change tenant headers:

- `VITE_ORGANIZATION_ID`
- `VITE_WORKSPACE_ID`
- `VITE_USER_ID`
- `VITE_WORKSPACE_NAME`

See `frontend/README.md` for the default UUIDs.

---

## Install backend

```bash
cd backend
uv sync
```

### Expected result (backend install)

- `uv` creates `backend/.venv`
- Dependencies install from the locked `uv.lock`
- Command exits successfully (no traceback)

Remain in `backend/` for database and backend start steps, or `cd` back when those
sections say so.

---

## Install frontend

From a **new** terminal (or after leaving `backend/`):

```bash
cd frontend
npm install
```

### Expected result (frontend install)

- `node_modules/` is created under `frontend/`
- Packages resolve using `package-lock.json`
- Command exits with a success summary (no hard install errors)

(`npm ci` is also supported for a lockfile-strict install; either is fine for first run.)

---

## Start infrastructure

From the **repository root**:

```bash
docker compose up -d
docker compose ps
```

### Expected result (infrastructure)

- Containers `rag-enterprise-postgres` and `rag-enterprise-redis` are **running**
- Postgres healthcheck becomes healthy (may take a few seconds)
- Ports `5432` (Postgres) and `6379` (Redis) are published on localhost

If containers fail to start, see [Troubleshooting](#troubleshooting).

---

## Database

Apply Alembic migrations from `backend/`:

```bash
cd backend
uv run alembic upgrade head
```

### Expected result (migrations)

- Alembic connects using `DATABASE_URL` / Postgres settings from `backend/.env`
- Revisions under `alembic/versions/` run through **head**
- Output resembles upgrade lines such as `Running upgrade … -> …` and ends without
  an error traceback

Knowledge, embeddings/indexing, and conversation tables are now available to the API.

---

## Start backend

From `backend/`:

```bash
cd backend
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

Leave this process running.

| Check | URL |
| --- | --- |
| Swagger / OpenAPI UI | <http://localhost:8000/docs> |
| Liveness | <http://localhost:8000/api/v1/live> |
| Readiness | <http://localhost:8000/api/v1/ready> |
| System inventory | <http://localhost:8000/api/v1/system> |

### How to verify readiness

1. Open <http://localhost:8000/api/v1/live> — expect HTTP **200** and `"status": "live"`.
2. Open <http://localhost:8000/api/v1/ready> — expect HTTP **200** (not **503**).
   Checks include configuration, DI, database, evaluation storage, and upload storage.
3. Optionally open <http://localhost:8000/api/v1/system> — expect `"version": "1.0.0"`.
4. Open <http://localhost:8000/docs> — interactive API docs load.

Startup creates `FILE_STORAGE_ROOT` and `EVALUATION_STORAGE_ROOT` (default
`eval-artifacts`) when missing.

---

## Start frontend

In a **second** terminal:

```bash
cd frontend
npm run dev
```

### Expected result (frontend start)

- Vite prints a local URL (normally <http://localhost:5173>)
- Opening that URL shows the operator console (Knowledge / Chat / Evaluation)

Dev proxy: browser calls to `/api` are forwarded to `VITE_API_BASE_URL`
(default `http://localhost:8000`).

---

## First Operator Workflow

Use the console at <http://localhost:5173>. Keep backend and frontend running.

Optional corpus: files under `demo/knowledge/` (Persian policies). Any small `.txt`
upload also works for a smoke test.

### 1. Create Knowledge Base

1. Open **Knowledge**.
2. Click **Create knowledge base**.
3. Enter a name (for demo corpus, language `fa` is appropriate).
4. Save.

**Expected result:** The KB appears in the list with status **`draft`**.

### 2. Upload document

1. Open the knowledge base.
2. Create or select a document, then upload a file (for example one file from
   `demo/knowledge/`).
3. Complete the upload so a document version exists with status **`uploaded`**.

**Expected result:** The document shows a current version; processing status is
**`uploaded`** (not yet indexed).

### 3. Process & Index

1. Open the document inspector.
2. Click **Process & Index**.
3. Wait for the request to finish (synchronous; no background worker).

**Expected result:** Progress reaches **Indexed** / `processing_status` =
**`indexed`**. Chunk and embedding counts are greater than zero on a successful run.

### 4. Publish

1. Return to the Knowledge base **list**.
2. On the draft KB row, click **Publish**.

**Expected result:** Status becomes **`active`**. Retrieval and Chat require an
active knowledge base.

### 5. Chat

1. Open **Chat**.
2. Select the published knowledge base.
3. Ask a question grounded in the uploaded text (demo prompt examples:
   `demo/questions/suggested-questions-fa.md`).

**Expected result:** A reply is returned. With `LLM_BACKEND=echo`, the answer is the
platform echo/grounded template path (not a third-party LLM). Prefer questions whose
answers appear in the indexed text.

### 6. Evidence panel

1. On a grounded (non-abstained) answer, open the evidence / citations UI in Chat.

**Expected result:** Citation or evidence entries reference retrieved chunks from
your indexed document.

### 7. Evaluation dashboard

1. Open **Evaluation** in the operator console.

**Expected result:** The Evaluation Dashboard loads and can list runs when Feature
007 offline experiment artifacts exist under the evaluation storage root.

> Offline evaluation **execution** (golden dataset → `EvaluationService`) is separate
> from the dashboard. For the full demo evaluation set, follow
> [Demo Guide](DEMO_GUIDE.md) and [Evaluation Guide](EVALUATION_GUIDE.md). An empty
> runs list on first boot is normal until you execute an offline run.

---

## Shutdown

Stop processes in reverse order of start when possible.

### Stop backend

In the backend terminal: press `Ctrl+C` to stop uvicorn.

### Stop frontend

In the frontend terminal: press `Ctrl+C` to stop Vite.

### Stop Docker

From the **repository root**:

```bash
docker compose down
```

This stops and removes the Compose containers. Add `--volumes` **only** if you
intend to delete local Postgres/Redis data (full database reset).

---

## Troubleshooting

### Docker not running

**Symptom:** `docker compose up` fails immediately; Docker daemon errors.

**Fix:** Start Docker Desktop (or the Docker service), wait until it is ready, retry
`docker compose up -d`.

### Database unavailable

**Symptom:** `/api/v1/ready` returns **503** with `database` failing; Alembic cannot
connect; backend logs connection refused / auth failure.

**Fix:**

1. `docker compose ps` — ensure Postgres is up and healthy.
2. Confirm `DATABASE_URL` / `POSTGRES_*` in `backend/.env` match Compose credentials
   in the root `.env`.
3. Wait a few seconds after first boot for healthchecks to pass, then retry readiness.

### Migration errors

**Symptom:** `uv run alembic upgrade head` fails.

**Fix:**

1. Run migrations only from `backend/` via `uv run alembic …`.
2. Confirm Postgres is reachable with the same URL the backend uses.
3. If the database was partially initialized and you can discard local data:
   `docker compose down --volumes`, then `docker compose up -d`, then migrate again.

### Storage folder

**Symptom:** Readiness fails on `upload_storage` or `evaluation_storage`; configuration
validation mentions `FILE_STORAGE_ROOT` / `EVALUATION_STORAGE_ROOT`.

**Fix:**

1. Ensure the process can create directories under the repo (or configured paths).
2. Prefer relative defaults (`storage/uploads`, `eval-artifacts`) while running from
   `backend/`.
3. Do not point `FILE_STORAGE_ROOT` at a read-only location.

### Port already used

**Symptom:** uvicorn or Vite refuse to bind; Compose cannot publish `5432` / `6379`.

**Fix:** Free the port or stop the conflicting process. Common local ports:

| Port | Service |
| --- | --- |
| 5432 | PostgreSQL (Compose) |
| 6379 | Redis (Compose) |
| 8000 | Backend API |
| 5173 | Frontend Vite |

### Backend imports / wrong directory

**Symptom:** `ModuleNotFoundError` or uv cannot find the project.

**Fix:** Always run backend commands from `backend/` with `uv run …` after `uv sync`.

### Frontend cannot reach API

**Symptom:** Network/API errors in the console; Knowledge calls fail.

**Fix:**

1. Confirm backend readiness at <http://localhost:8000/api/v1/ready>.
2. Confirm `VITE_API_BASE_URL=http://localhost:8000` (or restart Vite after changing it).
3. Use the Vite origin (proxy `/api`) rather than calling a wrong host/port in the browser.

### Knowledge / Chat surprises

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Chat / retrieve finds nothing | KB still `draft` or docs not `indexed` | **Publish** KB; re-run **Process & Index** |
| Chat abstains often | Deterministic embeddings + default evidence gate | Set `GENERATION_MIN_EVIDENCE_SCORE=0.0` in `backend/.env` and restart backend |
| Permission / actor issues | Missing development headers | Use the stock frontend defaults (`X-User-Id` / `X-Organization-Id` stub) |

---

## Related documents

- [Development Guide](DEVELOPMENT.md) — day-to-day quality commands
- [Demo Guide](DEMO_GUIDE.md) — official Persian demo corpus workflow
- [Evaluation Guide](EVALUATION_GUIDE.md) — offline evaluation details
- [Operational Health](backend/OPERATIONAL_HEALTH.md) — probe semantics
- [Configuration](backend/CONFIGURATION.md) — startup validation rules
- [Local File Storage](backend/LOCAL_FILE_STORAGE.md) — upload layout
- [Process & Index](backend/PROCESS_AND_INDEX.md) — operator orchestration
- [Release Notes](../RELEASE_NOTES.md)
