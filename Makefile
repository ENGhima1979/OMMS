# OMMS — Makefile for common operations
# نظام إدارة التشغيل والصيانة

.PHONY: help install dev seed test lint docker-up docker-down clean

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ─────────────────────────────────────────────────
install:       ## Install Python dependencies
	cd backend && pip install -r requirements.txt

dev:           ## Run development server with hot-reload
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

seed:          ## Seed database with demo data
	cd backend && python seed.py

test:          ## Run test suite
	cd backend && python -m pytest tests/ -v --tb=short

lint:          ## Lint and format code
	cd backend && python -m flake8 app/ --max-line-length=120 --exclude=__pycache__

# ── Docker ───────────────────────────────────────────────────────
docker-up:     ## Start all services with Docker Compose
	docker-compose up -d

docker-down:   ## Stop all services
	docker-compose down

docker-build:  ## Build Docker images
	docker-compose build

docker-logs:   ## Show container logs
	docker-compose logs -f

docker-seed:   ## Seed database in Docker container
	docker exec omms_api python seed.py

# ── Database ─────────────────────────────────────────────────────
migrate:       ## Run Alembic migrations
	cd backend && alembic upgrade head

migration:     ## Create new migration (use: make migration msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"

# ── Utilities ────────────────────────────────────────────────────
clean:         ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

open-docs:     ## Open API documentation in browser
	open http://localhost:8000/api/docs || xdg-open http://localhost:8000/api/docs

open-app:      ## Open frontend app in browser
	open http://localhost:3000 || xdg-open http://localhost:3000
