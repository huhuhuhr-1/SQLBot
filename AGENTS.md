# AGENTS.md

## Cursor Cloud specific instructions

### Project Overview

SQLBot is a ChatBI (conversational data analysis) system built on LLMs and RAG. It consists of three services:

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
EMBEDDING_ENABLED=false PYTHONPATH=/workspace/backend uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --reload
```
- Set `EMBEDDING_ENABLED=false` to skip loading the embedding model (which requires ~500MB model files at `/opt/sqlbot/models`). Without the model files, the backend still works for all features except vector similarity search.
- Alembic migrations run automatically on startup via the `lifespan` handler.
- Default admin credentials: `admin` / `SQLBot@123456`

**Frontend** (from `frontend/` directory, requires Node 22):
```
npm run dev
```
- The `dev` script runs `vue-tsc -b && vite`, which does type-checking before starting Vite. This takes ~20 seconds.
- API proxy is configured to `http://localhost:8000/api/v1` in `.env.development`.

**G2-SSR** (from `g2-ssr/` directory, requires Node 18):
```
node app.js
```
- The `g2-ssr` service requires Node 18 because `node-canvas` native bindings are incompatible with Node 22.

### Lint & Test Commands

- **Backend lint**: `cd backend && uv run ruff check .`
- **Backend format check**: `cd backend && uv run ruff format . --check`
- **Backend tests**: `cd /workspace && PYTHONPATH=/workspace/backend uv run --project backend pytest tests/ -v`
- **Frontend lint**: `cd frontend && npx eslint .`
- **Frontend type-check**: `cd frontend && npx vue-tsc -b`

### Key Gotchas

- The login endpoint (`POST /api/v1/login/access-token`) requires RSA-encrypted credentials. Use the frontend UI for login; direct API calls with plaintext credentials will fail.
- `g2-ssr` needs Node 18 while frontend needs Node 22. Use `nvm` to switch between them.
- Required directories: `/opt/sqlbot/images`, `/opt/sqlbot/data/excel`, `/opt/sqlbot/data/file`, `/opt/sqlbot/app/logs`.
- The backend `pyproject.toml` requires `python ==3.11.*`. Ensure Python 3.11 is available.
- `uv` is the package manager for the backend (no `uv.lock` file in repo; `uv sync` resolves from `pyproject.toml`).
- Frontend has no lockfile; uses `npm install`.
