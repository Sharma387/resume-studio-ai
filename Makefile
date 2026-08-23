.PHONY: dev test lint build clean install help lint-py test-pg smoke deploy

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

dev: ## Start development servers
	@echo "Starting backend..."
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
	@sleep 2
	@echo "Starting frontend..."
	cd frontend && npm run dev &
	@wait

dev-backend: ## Start backend only
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start frontend only
	cd frontend && npm run dev

test: ## Run all tests (JSON backend)
	cd backend && source .venv/bin/activate && python -m pytest tests/ --ignore=tests/test_auth.py

test-pg: ## Run all tests (PostgreSQL backend)
	cd backend && source .venv/bin/activate && \
		STORAGE_BACKEND=postgres DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai \
		python -m pytest tests/ --ignore=tests/test_auth.py

test-coverage: ## Run tests with coverage
	cd backend && source .venv/bin/activate && python -m pytest --cov=app

lint-py: ## Lint Python code (ruff)
	cd backend && source .venv/bin/activate && ruff check app/ && echo "✅ Lint passed"

format-py: ## Format Python code (ruff)
	cd backend && source .venv/bin/activate && ruff format app/

lint: ## Run all linters (alias for lint-py)
	$(MAKE) lint-py

build: ## Build frontend
	cd frontend && npm run build

db-up: ## Start PostgreSQL
	docker compose up -d postgres

db-migrate: ## Run Alembic migrations
	cd backend && source .venv/bin/activate && alembic upgrade head

smoke: ## Run production smoke tests
	cd backend && source .venv/bin/activate && \
		STORAGE_BACKEND=postgres DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai \
		python -m scripts.deployment.smoke_test

migrate-data: ## Migrate JSON data to PostgreSQL
	cd backend && source .venv/bin/activate && \
		DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai \
		python -m scripts.migrate_data --all

deploy: ## Run deployment steps (dry-run)
	cd backend && source .venv/bin/activate && \
		DATABASE_URL=postgresql://rsai:rsai@localhost:5432/rsai \
		STORAGE_BACKEND=postgres bash scripts/deployment/deploy.sh --dry-run

clean: ## Clean build artifacts
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf frontend/dist
	rm -rf .pytest_cache

docker-build: ## Build Docker image
	docker build -t resume-studio-ai .

tag: ## Create a new tag
	@read -p "Tag (e.g. v0.9): " tag; \
	git tag -a $$tag -m "$$tag" && git push origin $$tag
