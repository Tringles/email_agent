# Makefile for Email AI Aggregator

.PHONY: help install init-db migration migrate migrate-down migration-history test clean

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make init-db        - Initialize database (quick setup)"
	@echo "  make migration      - Create new migration (use: make migration msg='message')"
	@echo "  make migrate        - Apply migrations"
	@echo "  make migrate-down   - Rollback one migration"
	@echo "  make migration-history - Show migration history"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean cache files"

install:
	pip install -r requirements.txt

init-db:
	python scripts/init_db.py

# Alembic migrations
migration:
	@if [ -z "$(msg)" ]; then \
		echo "Usage: make migration msg='your message'"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(msg)"

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migration-history:
	alembic history

test:
	pytest -q

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true

