COMPOSE_FILE=infra/docker-compose.yml
ENV_FILE=infra/env/.env

.PHONY: up down ps logs restart

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

