COMPOSE_FILE=infra/docker-compose.yml
ENV_FILE=infra/env/.env

.PHONY: up down ps logs restart migrate seed

up:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Copy infra/env/.env.example to infra/env/.env and edit values"; \
		exit 1; \
	fi
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down

ps:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) ps

logs:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) logs -f

restart: down up

migrate:
	docker exec dc_api alembic upgrade head

seed:
	docker exec -e PGHOST=db -e PGPORT=5432 -e PGDATABASE=datacopilot -e PGUSER=datacopilot -e PGPASSWORD=datacopilot dc_db psql -U datacopilot -d datacopilot -c "select 1" > /dev/null
	docker cp scripts/seed.py dc_api:/tmp/seed.py
	docker exec dc_api python /tmp/seed.py

