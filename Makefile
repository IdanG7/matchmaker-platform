.PHONY: help up down logs restart clean seed test test-unit test-integration test-load build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose -f deployments/docker/docker-compose.yml up -d --build
	@echo "Services starting... waiting for database..."
	@sleep 5
	@echo "Running migrations..."
	docker compose -f deployments/docker/docker-compose.yml exec -T postgres psql -U postgres -d game -f /migrations/init.sql || true

down: ## Stop all services
	docker compose -f deployments/docker/docker-compose.yml down -v

logs: ## Follow logs from all services
	docker compose -f deployments/docker/docker-compose.yml logs -f --tail=200

restart: down up ## Restart all services

clean: down ## Clean all containers, volumes, and build artifacts
	docker system prune -f
	rm -rf services/matchmaker/build
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

seed: ## Seed database with test data
	docker run --rm --network docker_default \
		-e DATABASE_URL=postgresql://postgres:password@postgres:5432/game \
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
