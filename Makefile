.PHONY: test run-gateway run-core run-all docker-build docker-up docker-down

test:
	uv run aico dev test

# Run Gateway service (HTTP edge)
run-gateway:
	cd gateway && uv run python -m gateway.main

# Run Core service (NATS handlers, business logic)
run-core:
	cd core && uv run python -m core.main

# Run both services (requires separate terminals)
run-all:
	@echo "Start Gateway and Core in separate terminals:"
	@echo "  Terminal 1: make run-core"
	@echo "  Terminal 2: make run-gateway"

# Docker commands
docker-build:
	docker compose -f docker/docker-compose.local.yml build

docker-up:
	docker compose -f docker/docker-compose.local.yml up -d

docker-down:
	docker compose -f docker/docker-compose.local.yml down
