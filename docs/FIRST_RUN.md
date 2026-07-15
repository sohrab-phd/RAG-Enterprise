# First Run (Version 1.0.0)

Canonical bring-up guide for RAG-enterprise **Version 1.0.0** from a fresh clone.
Follow the sections **in order**.

**Directory rule:** Never assume which folder your shell is in. Every major section
starts with an explicit `cd`. Replace `/path/to/RAG-Enterprise` with the absolute
path to your clone (the folder that contains `backend/`, `frontend/`, and
`docker-compose.yml`).

This path uses:

- Local Docker Compose for PostgreSQL (pgvector) and Redis
- Backend defaults: `LLM_BACKEND=local` (Ollama chat — see [OLLAMA.md](backend/OLLAMA.md)).
  For a first demo **without** Ollama set `LLM_BACKEND=mock` (deterministic echo stub).
  Embeddings default to `EMBEDDING_BACKEND=deterministic` (no external model API keys required)
- The operator console for Knowledge, Chat, and Evaluation (sidebar links)

---

## Prerequisites

Install and verify the following on your machine. No repository directory is
required yet.

| Software | Recommended version | Notes |
| --- | --- | --- |
| Git | Any recent release | Clone and worktree |
| Docker Desktop | Current stable | Or Docker Engine **with Compose v2** |
| Python | **3.12+** | Required by `backend/pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Current stable | Backend package manager |
| Node.js | **20+** | Frontend runtime |
| npm | Bundled with Node | Frontend installs |

Verify (from any directory):

```bash
git --version
docker --version
docker compose version
python --version
uv --version
node --version
npm --version
```

On Windows, if `python` is missing, try `py -3 --version`.

Expected: each command prints a version; Python reports 3.12 or newer; Node reports
20 or newer; `docker compose version` succeeds (Compose v2).

---

## Clone repository

From any directory where you want the project to live:

```bash
git clone https://github.com/sohrab-phd/RAG-Enterprise.git
cd RAG-Enterprise
```

Remember this folder’s absolute path. You will use it as `/path/to/RAG-Enterprise`
in every later section.

---

## Environment

```bash
cd /path/to/RAG-Enterprise
```

Copy the example environment file at the **repository root** (used by Docker Compose):

```bash
# macOS / Linux / Git Bash
cp .env.example .env
```

```powershell
# Windows PowerShell (still inside /path/to/RAG-Enterprise)
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
| `VITE_API_BASE_URL` | Documented API base for the Vite proxy (default `http://localhost:8000`). The frontend works without a separate `frontend/.env` on first run; Vite defaults to this host if unset. |

### Recommended local additions (optional)

You may add these to `backend/.env` for a smoother first Chat experience with the
default **deterministic** embeddings (not semantic), or run local Ollama:

**Offline mock (no Ollama):**

```bash
LLM_BACKEND=mock
MOCK_PROVIDER=echo
EMBEDDING_BACKEND=deterministic
GENERATION_MIN_EVIDENCE_SCORE=0.0
```

**Local Ollama (recommended for real Persian answers):**

```bash
LLM_BACKEND=local
LOCAL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL_KEY=auto
LLM_TIMEOUT_SECONDS=120
```

Install Ollama, pull a model (`ollama pull <model>`), then restart the backend.
Details: [OLLAMA.md](backend/OLLAMA.md).

Without lowering the evidence score, Chat may abstain more often under deterministic
embeddings. `mock` and `deterministic` do **not** need API keys.

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
cd /path/to/RAG-Enterprise/backend
uv sync
```

### Expected result (backend install)

- `uv` creates `backend/.venv`
- Dependencies install from the locked `uv.lock`
- Command exits successfully (no traceback)

---

## Install frontend

```bash
cd /path/to/RAG-Enterprise/frontend
npm install
```

### Expected result (frontend install)

- `node_modules/` is created under `frontend/`
- Packages resolve using `package-lock.json`
- Command exits with a success summary (no hard install errors)

(`npm ci` is also supported for a lockfile-strict install; either is fine for first run.)

---

## Start infrastructure

```bash
cd /path/to/RAG-Enterprise
docker compose up -d
```

### Verify PostgreSQL is healthy

Wait until Postgres reports **healthy** before running migrations.

```bash
cd /path/to/RAG-Enterprise
docker compose ps
```

### Expected result (infrastructure)

- Containers `rag-enterprise-postgres` and `rag-enterprise-redis` are **running**
- `rag-enterprise-postgres` shows status **healthy** (not only “Up”)
- Ports `5432` (Postgres) and `6379` (Redis) are published on localhost

If Postgres is still starting, wait a few seconds and run `docker compose ps` again.
Only continue to the Database section after Postgres is healthy.

If containers fail to start, see [Troubleshooting](#troubleshooting).

---

## Database

Run migrations only after [Start infrastructure](#start-infrastructure) shows a
**healthy** Postgres container.

```bash
cd /path/to/RAG-Enterprise/backend
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

Leave this terminal open after starting the process.

```bash
cd /path/to/RAG-Enterprise/backend
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

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
4. Open <http://localhost:8000/docs> — interactive API docs (Swagger) load.

Startup creates `FILE_STORAGE_ROOT` and `EVALUATION_STORAGE_ROOT` (default
`eval-artifacts`) when missing.

---

## Start frontend

Use a **second** terminal (keep the backend terminal running).

```bash
cd /path/to/RAG-Enterprise/frontend
npm run dev
```

### Expected result (frontend start)

- Vite prints a local URL (normally <http://localhost:5173>)
- Opening that URL shows the operator console

Use the **left sidebar** to move between:

| Sidebar item | Route | Purpose |
| --- | --- | --- |
| **Knowledge** | `/knowledge` | Knowledge bases, uploads, Process & Index, Publish |
| **Chat** | `/chat` | Grounded Q&A with citations and Evidence |
| **Evaluation** | `/evaluation` | Evaluation Dashboard (run artifacts) |

Dev proxy: browser calls to `/api` are forwarded to `VITE_API_BASE_URL`
(default `http://localhost:8000`).

---

## First Operator Workflow

Use the console at <http://localhost:5173>. Keep backend and frontend running.

Optional corpus: files under `/path/to/RAG-Enterprise/demo/knowledge/` (Persian
policies). Any small `.txt` file also works for a smoke test.

Recommended end-to-end UI flow:

```text
Knowledge
  → Open Knowledge Base
  → Upload
  → Choose files
  → Start Upload
  → Process & Index
  → Publish
  → Chat (sidebar)
  → Evidence panel
  → Evaluation (sidebar)
```

### 1. Create Knowledge Base

1. In the sidebar, open **Knowledge**.
2. Click **Create knowledge base**.
3. Enter a name. For the demo corpus, set **Default language** to `fa`.
4. Save.

**Expected result:** The KB appears in the list with status **`draft`**.

### 2. Upload

1. In the Knowledge list, click the knowledge base **name** to open it.
2. Click **Upload**.
3. Choose one or more files (for example from `demo/knowledge/`).
4. Click **Start upload**.
5. Wait until the upload row shows **completed**.

Do **not** create documents manually — the Upload flow creates the document and
version for you.

**Expected result:** A new document appears in the KB. Open it; processing status is
**`uploaded`** (not yet indexed).

### 3. Process & Index

1. With the uploaded document selected, find the processing panel.
2. Click **Process & Index**.
3. Wait for the request to finish (synchronous; no background worker).

**Expected result:** Progress reaches **Indexed** / `processing_status` =
**`indexed`**.

### 4. Publish

1. In the sidebar, open **Knowledge** again (knowledge base **list**).
2. On the draft KB row, click **Publish**.

**Expected result:** Status becomes **`active`**. Retrieval and Chat require an
active knowledge base.

### 5. Chat

1. In the sidebar, open **Chat**.
2. Select the published knowledge base.
3. Ask a question grounded in the uploaded text (examples:
   `demo/questions/suggested-questions-fa.md`).

**Expected result:** An assistant reply is returned. With `LLM_BACKEND=mock`
(echo stub), responses are deterministic grounded answers suitable for demos.
With `LLM_BACKEND=local`, Ollama generates answers ([OLLAMA.md](backend/OLLAMA.md)).
`LLM_BACKEND=api` uses an OpenAI-compatible remote model. Prefer questions whose
answers appear in the indexed text.

### 6. Evidence panel

1. After the assistant answer appears, use the **Evidence** panel in Chat
   (desktop: side panel; on small screens use the Evidence tab if shown).

**Expected result:** The Evidence panel appears after the answer and shows citation
/ retrieved-chunk evidence for grounded replies.

### 7. Evaluation dashboard

1. In the sidebar, open **Evaluation**.

**Expected result:** The Evaluation page opens. The dashboard can **legitimately be
empty** until an offline evaluation run exists. An empty runs list on first boot is
normal.

> Offline evaluation **execution** (golden dataset → `EvaluationService`) is separate
> from the dashboard. For the full demo evaluation set, follow
> [Demo Guide](DEMO_GUIDE.md) and [Evaluation Guide](EVALUATION_GUIDE.md).

---

## Shutdown

Stop processes in reverse order of start when possible.

### Stop backend

In the terminal where uvicorn is running: press `Ctrl+C`.

### Stop frontend

In the terminal where Vite is running: press `Ctrl+C`.

### Stop Docker

```bash
cd /path/to/RAG-Enterprise
docker compose down
```

This stops and removes the Compose containers. Add `--volumes` **only** if you
intend to delete local Postgres/Redis data (full database reset).

---

## First-run checklist

The project is correctly running if **all** of the following are true:

- [ ] `/ready` returns **200** — <http://localhost:8000/api/v1/ready>
- [ ] Swagger opens — <http://localhost:8000/docs>
- [ ] Frontend opens — <http://localhost:5173>
- [ ] Knowledge Base is **Active** (Published)
- [ ] Document is **Indexed** (Process & Index completed)
- [ ] Chat answers (Echo grounded reply for an in-corpus question)
- [ ] Evidence appears after the assistant answer
- [ ] Evaluation page opens (empty run list is OK on first boot)

---

## Troubleshooting

### Docker not running

**Symptom:** `docker compose up` fails immediately; Docker daemon errors.

**Fix:** Start Docker Desktop (or the Docker service), wait until it is ready, then:

```bash
cd /path/to/RAG-Enterprise
docker compose up -d
```

### Database unavailable

**Symptom:** `/api/v1/ready` returns **503** with `database` failing; Alembic cannot
connect; backend logs connection refused / auth failure.

**Fix:**

1. Confirm directory and health:

   ```bash
   cd /path/to/RAG-Enterprise
   docker compose ps
   ```

   Postgres must be **healthy** before migrations or API traffic.
2. Confirm `DATABASE_URL` / `POSTGRES_*` in `backend/.env` match Compose credentials
   in the root `.env`.
3. Wait until healthy, then retry readiness.

### Migration errors

**Symptom:** `uv run alembic upgrade head` fails.

**Fix:**

1. Ensure Postgres is healthy (`docker compose ps` from `/path/to/RAG-Enterprise`).
2. Run migrations only from backend:

   ```bash
   cd /path/to/RAG-Enterprise/backend
   uv run alembic upgrade head
   ```

3. If the database was partially initialized and you can discard local data:

   ```bash
   cd /path/to/RAG-Enterprise
   docker compose down --volumes
   docker compose up -d
   ```

   Wait for healthy Postgres, then migrate again from `backend/`.

### Storage folder

**Symptom:** Readiness fails on `upload_storage` or `evaluation_storage`; configuration
validation mentions `FILE_STORAGE_ROOT` / `EVALUATION_STORAGE_ROOT`.

**Fix:**

1. Ensure the process can create directories under the repo (or configured paths).
2. Prefer relative defaults (`storage/uploads`, `eval-artifacts`) while running from
   `/path/to/RAG-Enterprise/backend`.
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

**Fix:**

```bash
cd /path/to/RAG-Enterprise/backend
uv sync
uv run uvicorn rag_enterprise.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend cannot reach API

**Symptom:** Network/API errors in the console; Knowledge calls fail.

**Fix:**

1. Confirm backend readiness at <http://localhost:8000/api/v1/ready>.
2. Restart Vite after changing any frontend env override:

   ```bash
   cd /path/to/RAG-Enterprise/frontend
   npm run dev
   ```

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
