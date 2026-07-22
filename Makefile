.PHONY: dev test lint build clean install help

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

test: ## Run all tests
	cd backend && source .venv/bin/activate && python -m pytest

test-coverage: ## Run tests with coverage
	cd backend && source .venv/bin/activate && python -m pytest --cov=app

lint: ## Run all linters
	cd frontend && npm run lint

build: ## Build frontend
	cd frontend && npm run build

clean: ## Clean build artifacts
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf frontend/dist
	rm -rf .pytest_cache

docker-build: ## Build Docker image
	docker build -t resume-studio-ai .

db-setup: ## Initialize database (future PostgreSQL)
	@echo "Database setup not yet configured"

tag: ## Create a new tag
	@read -p "Tag (e.g. v0.9): " tag; \
	git tag -a $$tag -m "$$tag" && git push origin $$tag
