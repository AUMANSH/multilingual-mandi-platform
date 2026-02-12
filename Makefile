# Multilingual Mandi Platform - Development Makefile

.PHONY: help install install-dev test test-unit test-property test-integration test-coverage lint format clean docker-build docker-up docker-down

# Default target
help:
	@echo "Available targets:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-property    Run property-based tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  clean            Clean up temporary files"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-up        Start services with docker-compose"
	@echo "  docker-down      Stop services with docker-compose"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing targets
test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "unit"

test-property:
	pytest tests/ -v -m "property" --tb=short

test-integration:
	pytest tests/ -v -m "integration"

test-coverage:
	pytest tests/ --cov=src/mandi_platform --cov-report=term-missing --cov-report=html

test-fast:
	pytest tests/ -v -x --tb=short -m "not slow"

# Code quality targets
lint:
	flake8 src/ tests/
	mypy src/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

# Cleanup targets
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Docker targets
docker-build:
	docker build -t multilingual-mandi-platform .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database targets
db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-revision:
	alembic revision --autogenerate -m "$(MESSAGE)"

db-reset:
	alembic downgrade base
	alembic upgrade head

# Development server
dev:
	uvicorn mandi_platform.main:app --reload --host 0.0.0.0 --port 8000

# Property-based test specific targets
test-property-verbose:
	pytest tests/ -v -m "property" --hypothesis-show-statistics --tb=long

test-property-examples:
	pytest tests/test_property_examples.py -v --hypothesis-show-statistics

# CI/CD targets
ci-test:
	pytest tests/ --cov=src/mandi_platform --cov-report=xml --cov-fail-under=80

ci-lint:
	flake8 src/ tests/ --format=github
	mypy src/ --junit-xml=mypy-results.xml
	black --check src/ tests/
	isort --check-only src/ tests/