.PHONY: help up down logs restart clean seed migrate test test-unit test-integration test-load build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

COMPOSE := docker compose -f deployments/docker/docker-compose.yml
ENV_FILE := deployments/docker/.env

# Credentials come from the same env file compose reads, so migrations cannot
# drift from the database that was actually created.
POSTGRES_USER := $(shell grep -E '^POSTGRES_USER=' $(ENV_FILE) 2>/dev/null | cut -d= -f2)
POSTGRES_DB := $(shell grep -E '^POSTGRES_DB=' $(ENV_FILE) 2>/dev/null | cut -d= -f2)

$(ENV_FILE):
	@echo "Missing $(ENV_FILE). Create it with:"
	@echo "    cp deployments/docker/.env.example $(ENV_FILE)"
	@echo "then set JWT_SECRET_KEY to a random value."
	@exit 1

up: $(ENV_FILE) ## Start all services and run migrations
	$(COMPOSE) up -d --build
	@echo "Waiting for postgres..."
	@until $(COMPOSE) exec -T postgres pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) >/dev/null 2>&1; do sleep 1; done
	@echo "Running migrations..."
	$(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB) -f /migrations/init.sql
	@echo "Stack is up. API at http://localhost:8080/docs"

migrate: $(ENV_FILE) ## Re-run database migrations
	$(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB) -f /migrations/init.sql

down: ## Stop all services
	$(COMPOSE) down -v

logs: ## Follow logs from all services
	$(COMPOSE) logs -f --tail=200

restart: down up ## Restart all services

clean: down ## Clean all containers, volumes, and build artifacts
	docker system prune -f
	rm -rf services/matchmaker/build
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

seed: $(ENV_FILE) ## Seed database with test data
	docker run --rm --network docker_default \
		-e DATABASE_URL=postgresql://$(POSTGRES_USER):$(shell grep -E '^POSTGRES_PASSWORD=' $(ENV_FILE) | cut -d= -f2)@postgres:5432/$(POSTGRES_DB) \
		-v $(PWD)/scripts:/scripts \
		python:3.12-slim \
		sh -c "pip install -q -r /scripts/requirements.txt && python /scripts/seed_players.py"

test: test-unit ## Run all tests

test-unit: ## Run unit tests
	@echo "Running Python unit tests..."
	pytest tests/unit -v
	@echo "Running C++ unit tests..."
	cd services/matchmaker && cmake -B build && cmake --build build && ctest --test-dir build --output-on-failure

test-integration: ## Run integration tests
	pytest tests/integration -v

test-load: ## Run load tests
	cd tests/load && locust -f locustfile.py --headless -u 100 -r 10 --run-time 60s

build: ## Build all services locally
	@echo "Building Python services..."
	pip install -r services/api/requirements.txt
	@echo "Building C++ matchmaker..."
	cd services/matchmaker && cmake -B build && cmake --build build
	@echo "Building C++ SDK..."
	cd sdk/cpp && cmake -B build && cmake --build build
