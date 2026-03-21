DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: dev dev-down dev-logs dev-restart

dev:
	$(DEV) up -d --build
	$(DEV) logs -f

dev-down:
	$(DEV) down

dev-logs:
	$(DEV) logs -f

dev-restart:
	$(DEV) down
	$(DEV) up -d --build
