.PHONY: help env install migrate backend frontend test test-backend test-frontend lint bootstrap ingest weather climate up down logs

help:
	@echo "Civic Climate Intelligence Platform"
	@echo "  make install        Install backend + frontend dependencies"
	@echo "  make migrate        Apply database migrations"
	@echo "  make bootstrap      Import Kolkata boundary, localities and 1 km grid"
	@echo "  make backend        Run Django development server (port 8000)"
	@echo "  make frontend       Run Vite development server (port 5173)"
	@echo "  make test           Run backend + frontend tests"
	@echo "  make lint           Run ruff + ESLint + TypeScript checks"
	@echo "  make up / down      Docker Compose stack (requires Docker)"
	@echo "  make weather        Ingest current + forecast weather for Kolkata"
	@echo "  make climate        Ingest ERA5-Land climate history for Kolkata"

env:
	@test -f .env || cp .env.example .env

install:
	python -m pip install -r backend/requirements/dev.txt
	cd frontend && npm install

migrate:
	cd backend && python manage.py migrate

bootstrap:
	cd backend && python manage.py bootstrap_kolkata

backend:
	cd backend && python manage.py runserver 0.0.0.0:8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -q

test-frontend:
	cd frontend && npm test -- --run

lint:
	cd backend && python -m ruff check .
	cd frontend && npm run lint
	cd frontend && npm run typecheck

weather:
	cd backend && python manage.py fetch_weather --area kolkata

climate:
	cd backend && python manage.py fetch_climate --area kolkata

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend
