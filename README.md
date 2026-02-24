# Data CoPilot — Proof of Concept (POC)

> **Status:** Early-stage POC. Core infrastructure runs locally; API, web, and workers are scaffolded but not yet implemented.

This repository is a proof of concept for a **local-first, chat-centric Data CoPilot**. The POC focuses on learning the technology stack step-by-step, with a scalable foundation that can evolve from CSV/Postgres today to Parquet, Databricks, Snowflake, or other infrastructure tomorrow.

---

## What This POC Covers

A context-aware Data CoPilot that routes user messages to internal agents (profiling, harmonization, governance/doc gen) using LangChain + LangGraph. Core workflows:

- **Context-aware Q&A** — RAG over selected Project/Subfolder/files with citations
- **Dataset profiling** — Column stats, patterns, rule checks, downloadable reports
- **Harmonization** — Bronze → silver → gold (planned; out of v1 POC scope)
- **Governance doc generation** — Template-based docs from uploaded rules (planned; out of v1 POC scope)

Tech baseline: **React SPA + FastAPI + Postgres (pgvector) + Redis + MinIO**.

---

## Current POC State

### ✅ Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| **Infrastructure** | Ready | Postgres 16, Redis 7, MinIO via Docker Compose |
| **Makefile** | Ready | `make up`, `make down`, `make ps`, `make logs`, `make restart` |
| **Environment** | Partial | `infra/env/.env` for local config; `.env.example` to be added |
| **Folder structure** | Scaffolded | `apps/`, `workers/`, `packages/`, `db/`, `scripts/`, `docs/` |

### 🚧 Placeholders (not yet implemented)

| Component | Location | Planned |
|-----------|----------|---------|
| **API** | `apps/api/` | FastAPI with `/healthz`, `/profiling/run`, `/jobs/{id}`, `/artifacts/{id}/signed-url` |
| **Web** | `apps/web/` | React SPA (Vite) with chat UI, Run Profile button, artifact links |
| **Profiling worker** | `workers/profiling/` | RQ consumer → Postgres stats → MinIO artifact → DB update |
| **Shared schemas** | `packages/shared/` | Pydantic models, job payloads, event contracts |
| **DB migrations** | `db/migrations/` | Alembic; tables: project, subfolder, thread, turn, artifact, profile_run, profile_result |
| **Scripts** | `scripts/` | MinIO bucket bootstrap, seed data, dev utilities |
| **Docs** | `docs/` | ADRs, diagrams, interface contracts |

### Infra Services (Docker Compose)

- **db** — Postgres 16 (pgvector planned)
- **redis** — Queue and cache
- **minio** — S3-compatible object storage (buckets: `uploads`, `artifacts`, `evidence`)

---

## Project Structure

```
apps/
  api/                # FastAPI service (skeleton)
  web/                # React SPA (skeleton)
workers/
  profiling/          # Profiling worker (skeleton)
db/
  migrations/         # Alembic migrations (placeholder)
infra/
  docker-compose.yml  # Postgres, Redis, MinIO
  env/                # .env (local); .env.example (to add)
packages/
  shared/             # Shared types/schemas (placeholder)
scripts/              # Dev scripts (placeholder)
docs/                 # Documentation (placeholder)
```

---

## Getting Started

### Prerequisites

- **Docker Desktop** (includes Compose v2). Verify: `docker --version`, `docker compose version`
- **make** (optional; use direct Compose commands if not available)

### Setup

1. **Environment file** — Copy the example and add your secrets:

   ```bash
   cp infra/env/.env.example infra/env/.env
   ```

   Edit `infra/env/.env` and fill in real values (the `.env` file is gitignored and will not be committed).

2. **Start infrastructure:**

   ```bash
   make up
   ```

3. **Verify services:**

   ```bash
   make ps
   docker exec -it dc_db psql -U datacopilot -d datacopilot -c "select 1;"
   docker exec -it dc_redis redis-cli ping   # expect PONG
   ```

4. **MinIO console** — Open http://localhost:9001, create buckets: `uploads`, `artifacts`, `evidence`.

### Ports

| Service | Port | Purpose |
|---------|------|---------|
| Postgres | 5432 | Database |
| Redis | 6379 | Queue / cache |
| MinIO API | 9000 | S3 API |
| MinIO Console | 9001 | Web UI |

---

## Planned Next Steps (POC v1)

1. **API-first** — FastAPI app with `/healthz`, Dockerfile, add `api` service to Compose.
2. **DB migrations** — Initial Alembic migrations for `project`, `subfolder`, `thread`, `turn`, `artifact`, `profile_run`, `profile_result`.
3. **Profiling worker** — RQ worker that consumes jobs, computes basic stats, writes artifact to MinIO.
4. **Web MVP** — Vite + React page with Run Profile button, status polling, artifact download link.

---

## Reference

- **Blueprint** — See `ProjectDescription.txt` for the full product vision, data model, and workflows (currently gitignored; un-ignore to reference).
- **Component READMEs** — Each folder (`apps/api`, `apps/web`, `workers/profiling`, etc.) has a README with implementation notes.

---

## License

(Add as needed)
