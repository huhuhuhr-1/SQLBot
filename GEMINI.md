# GEMINI.md - SQLBot Project Context

This file provides instructional context for Gemini CLI when working on the SQLBot project.

## Project Overview

SQLBot is an open-source, AI-powered Text-to-SQL system (ChatBI) based on Large Language Models (LLM) and Retrieval-Augmented Generation (RAG). It enables users to perform conversational data analysis and generate visualizations.

- **Backend**: Python 3.11, FastAPI, SQLModel (SQLAlchemy-based), Alembic (migrations), LangChain (LLM orchestration), Pydantic v2.
- **Frontend**: Vue 3, TypeScript, Vite, Element Plus, AntV G2/S2/X6 (charts/graphs).
- **Database**: PostgreSQL (main storage), Vector store (pgvector) for RAG.
- **Infrastructure**: Docker, Kubernetes (Helm), Offline installer support.
- **Key Features**: Text-to-SQL, RAG with terminology support, Workspace-level security, MCP integration, Dashboarding.

## Directory Structure

- `backend/`: Python FastAPI application logic, models, and API.
- `frontend/`: Vue 3 source code and build configurations.
- `build/`: Docker build scripts and multi-platform support.
- `deploy/`: Helm charts and Kubernetes deployment manifests.
- `docs/`: Comprehensive project documentation (GUIDE, DEBUG, ARCHITECTURE).
- `installer/`: Scripts for offline installation.
- `g2-ssr/`: Node.js service for server-side rendering of charts.

## Building and Running

### Local Development

#### Backend
```bash
cd backend
uv sync # Install dependencies using uv
# Copy .env.example to .env and configure DATABASE_URL, etc.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker Build

The project uses a two-stage build process for efficiency:
- **Base Build** (Slow): Builds dependencies and frontend.
  `cd build && ./build.sh base`
- **Quick Build** (Fast): Updates only backend code on top of the base image.
  `cd build && ./build.sh quick`
- **One-click Build**:
  `./quick.sh`

## Development Conventions

- **Linting & Formatting**: 
  - Backend: Uses `ruff` and `mypy`. Run `backend/scripts/lint.sh` and `backend/scripts/format.sh`.
  - Frontend: Uses `eslint` and `prettier`. Run `npm run lint`.
- **Testing**:
  - Backend: Uses `pytest`. Run `backend/scripts/test.sh`.
- **Database Migrations**:
  - Managed by Alembic. Run migrations using `alembic upgrade head` or through the application's startup lifespan.
  - New migrations: `alembic revision --autogenerate -m "description"`.
- **Environment Variables**:
  - All configurations should be defined in `backend/common/core/config.py` using `pydantic-settings`.
  - Use `.env` file at the project root or in `backend/`.
- **LLM Integration**:
  - LLM configurations are managed in `backend/apps/ai_model/model_factory.py`.
  - Prompts are stored in `backend/templates/template.yaml`.

## Key Commands Reference

| Task | Command |
|------|---------|
| Install Backend Deps | `cd backend && uv sync` |
| Start Backend | `cd backend && uvicorn main:app --reload` |
| Install Frontend Deps | `cd frontend && npm install` |
| Start Frontend | `cd frontend && npm run dev` |
| Run Backend Tests | `cd backend && pytest` |
| Lint Backend | `cd backend && ruff check .` |
| Build Base Image | `cd build && ./build.sh base` |
| Build Quick Image | `cd build && ./build.sh quick` |

## Documentation Links
- [Complete Guide](docs/GUIDE.md)
- [Debug Guide](docs/DEBUG.md)
- [Build Documentation](build/README.md)
