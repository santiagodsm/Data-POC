# Data CoPilot — POC v1

> **Status:** MVP running locally. Full stack is live — upload a CSV, profile it, download the report.

A local-first Data CoPilot built step-by-step as a learning project. The foundation is intentionally swappable: CSV + Postgres today, Parquet + Databricks/Snowflake tomorrow.

---

## What's Running

| Component | Status | Notes |
|-----------|--------|-------|
| **Infra** | ✅ | Postgres 16, Redis 7, MinIO — Docker Compose |
| **API** | ✅ | FastAPI — upload, profiling, artifact download |
| **DB migrations** | ✅ | Alembic — 7 tables |
| **Profiling worker** | ✅ | RQ consumer — column stats → MinIO → DB |
| **Web UI** | ✅ | React + Vite — CSV upload, profile, download |
| **Seed data** | ✅ | `make seed` — sample projects, threads, turns |

---

## Services & Ports

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:5173 | React + Vite frontend |
| API | http://localhost:8000 | FastAPI backend |
| API docs | http://localhost:8000/docs | Swagger UI |
| MinIO console | http://localhost:9001 | Object storage UI |
| Postgres | localhost:5432 | Database |
| Redis | localhost:6379 | Job queue |

---

## Getting Started

### Prerequisites

- **Docker Desktop** — `docker --version` and `docker compose version`
- **make**

### Setup

```bash
# 1. Copy env file and fill in your values
cp infra/env/.env.example infra/env/.env

# 2. Start everything
make up

# 3. Run migrations
make migrate

# 4. (Optional) Seed sample data
make seed
```

Open **http://localhost:5173**.

---

## API Endpoints

```
GET  /healthz                          Health check
POST /upload                           Upload a CSV → creates a Postgres table
POST /profiling/run                    Enqueue a profiling job
GET  /profiling/runs/{id}              Poll job status + result
GET  /profiling/runs/{id}/download     Download the JSON report artifact
```

---

## How It Works

```
Browser → POST /upload
            → parses CSV, creates table in Postgres, saves file to MinIO

Browser → POST /profiling/run
            → inserts profile_run row (status: pending)
            → enqueues job in Redis

RQ Worker → dequeues job
            → queries Postgres for column stats (row count, null %, distinct count)
            → writes JSON report to MinIO (artifacts bucket)
            → inserts artifact + profile_result rows
            → updates profile_run.status = done

Browser → GET /profiling/runs/{id}     (polling every 1s)
            → returns status + result when done

Browser → GET /profiling/runs/{id}/download
            → streams JSON report from MinIO through the API
```

---

## Project Structure

```
apps/
  api/                    FastAPI service
    app/
      main.py             Endpoints: /upload, /profiling/*, /healthz
      models.py           SQLAlchemy 2.0 table definitions
      db.py               Session factory
      queue.py            RQ queue client
      storage.py          MinIO client
    alembic/              Migrations
    Dockerfile
    requirements.txt
  web/                    React + Vite SPA
    src/
      App.jsx             CSV upload + profiling UI
    vite.config.js        Dev server + API proxy
    Dockerfile

workers/
  profiling/
    tasks.py              run_profile() — stats, MinIO upload, DB update
    worker.py             RQ worker entry point
    Dockerfile

db/
  migrations/             Alembic config lives in apps/api/alembic/

infra/
  docker-compose.yml      All 6 services
  env/
    .env.example          Template — copy to .env

scripts/
  seed.py                 Insert sample projects, subfolders, threads, turns
```

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `project` | Top-level workspace |
| `subfolder` | Folder within a project |
| `thread` | Chat conversation |
| `turn` | Single message in a thread (role: user/assistant) |
| `artifact` | File stored in MinIO (key, bucket, content_type) |
| `profile_run` | A profiling job (pending → running → done/failed) |
| `profile_result` | Output + JSON summary of a profile run |

---

## Make Targets

```bash
make up        # Start all Docker services
make down      # Stop all services
make ps        # Show service status
make logs      # Tail all logs
make restart   # down + up
make migrate   # Run Alembic migrations (alembic upgrade head)
make seed      # Insert sample data
```

---

## Planned Next Steps

- **Context picker** — project/subfolder selector in the UI
- **Chat / Q&A** — RAG over uploaded files with citations (LangChain + pgvector)
- **Harmonization** — Bronze → silver → gold pipeline
- **Governance doc gen** — Template-based docs from uploaded rules

---

## License

(Add as needed)
