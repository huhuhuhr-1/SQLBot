# AGENTS.md

## Cursor Cloud specific instructions

### Project Overview

SQLBot is a ChatBI (conversational data analysis) system built on LLMs and RAG. The `feature/oidc` branch adds deep analysis, statistics analytics, data dictionary, metric config, and OIDC authentication on top of the base product.

| Service | Directory | Tech Stack | Dev Port |
|---------|-----------|-----------|----------|
| Backend API | `backend/` | Python 3.11, FastAPI, SQLModel, Alembic | 8000 |
| Frontend | `frontend/` | Vue 3, TypeScript, Vite, Element Plus | 5173 |
| G2-SSR (chart rendering) | `g2-ssr/` | Node.js 18, Express, node-canvas, PM2 | 3000 |

PostgreSQL 16 with pgvector extension is required as the database.

### Running Services

**PostgreSQL** must be started before the backend:
```
sudo pg_ctlcluster 16 main start
```

**Backend** (from `backend/` directory):
```
EMBEDDING_ENABLED=false PYTHONPATH=/workspace/backend .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --reload
```
- Set `EMBEDDING_ENABLED=false` to skip loading the embedding model (requires ~500MB model files at `/opt/sqlbot/models`). Without models, all features work except vector similarity search.
- Alembic migrations run automatically on startup via the `lifespan` handler.
- Default admin credentials: `admin` / `SQLBot@123456`
- Use `.venv/bin/` directly instead of `uv run` to avoid re-resolving torch (the `uv.lock` may trigger large downloads).

**Frontend** (from `frontend/` directory, requires Node 22):
```
npm run dev
```
- The `dev` script runs `vue-tsc -b && vite`, type-checking takes ~20 seconds before Vite starts.
- API proxy configured to `http://localhost:8000/api/v1` in `.env.development`.

**G2-SSR** (from `g2-ssr/` directory, requires Node 18):
```
node app.js
```
- Requires Node 18 because `node-canvas` native bindings are incompatible with Node 22.

### Lint & Test Commands

- **Backend lint**: `cd backend && .venv/bin/ruff check .`
- **Backend format check**: `cd backend && .venv/bin/ruff format . --check`
- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend type-check**: `cd frontend && npx vue-tsc -b`
- No formal pytest tests exist on this branch; `backend/test/` contains manual utility scripts.

### Key Gotchas

- The login endpoint (`POST /api/v1/login/access-token`) requires RSA-encrypted credentials. Use the frontend UI for login; direct API calls with plaintext credentials will fail.
- `g2-ssr` needs Node 18 while frontend needs Node 22. Use `nvm` to switch.
- Required directories: `/opt/sqlbot/images`, `/opt/sqlbot/data/excel`, `/opt/sqlbot/data/file`, `/opt/sqlbot/app/logs`.
- Backend `pyproject.toml` requires `python ==3.11.*`.
- `uv` is the backend package manager. A `uv.lock` file exists on this branch. Prefer running `.venv/bin/<command>` directly over `uv run` to avoid re-resolving the full torch dependency tree on every invocation.
- Frontend has no lockfile; uses `npm install`.
- The `main.py` proactively clears proxy env vars (`HTTP_PROXY`, `HTTPS_PROXY`, etc.) to avoid LangChain/httpx errors.
