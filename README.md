# Data CoPilot (Local-First, Profiling-First MVP)

This repository hosts a local-first, chat-centric Data CoPilot. MVP v1 focuses on profiling with strong provenance and per-turn context control. Harmonization and governance doc generation will follow.

## Structure

```
apps/
  api/                # FastAPI service (skeleton)
  web/                # React SPA (skeleton)
workers/
  profiling/          # Profiling worker (skeleton)
db/
  migrations/         # Alembic migrations (to be added)
infra/
  docker-compose.yml  # Core services: Postgres, Redis, MinIO
  env/.env.example    # Example environment variables
packages/
  shared/             # Shared types/schemas (to be added)
scripts/              # Dev scripts (to be added)
docs/                 # Docs & ADRs (to be added)
ProjectDescription.txt
```

## Getting Started (after scaffolding services)

1) Copy environment variables:

```
cp infra/env/.env.example infra/env/.env
```

2) Start core infrastructure:

```
make up
```

3) Next steps (will be added incrementally):
- Add base DB migrations (pgvector + app tables).
- Add API health endpoint and profiling job stub.
- Add worker skeleton to consume jobs and write a placeholder artifact to MinIO.
- Add minimal web page to trigger profiling and show artifact link.

Refer to `ProjectDescription.txt` for the full blueprint and the "Decisions" section for current choices.

