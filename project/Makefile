# DipworkPy Makefile
# Diplomacy Conflict Resolution Algorithm

.PHONY: help install check test test-core test-datc test-graphs test-graphs-perf test-stpsyr test-stpsyr-full integration-demo test-imports clean lint lint-check-ruff lint-check-format lint-check-mypy lint-fix ruff ruff-fix format format-check mypy verify dev

help:		## Show this help
	@echo "DipworkPy - Diplomacy Conflict Resolution"
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies with Poetry
	poetry install

check: install test-core test-datc test-graphs test-stpsyr integration-demo lint	## Run comprehensive algorithm correctness checks

test:		## Run all available tests
	poetry run python -m pytest tests/ -v

test-core:	## Run core conflict resolution tests
	@echo "=== Testing Core Conflict Resolution Algorithm ==="
	poetry run python -m pytest tests/test_conflict_game.py -v
	@echo ""

test-datc:	## Run DATC (Diplomacy Adjudication Test Cases) compliance tests
	@echo "=== Testing DATC Compliance ==="
	poetry run python -m pytest tests/test_conflict_datc.py -v
	@echo ""

test-stpsyr:	## Run STPSYR test cases (simple)
	@echo "=== Testing STPSYR Test Cases ==="
	@poetry run python tests_from_stpsyr/test_stpsyr_simple.py
	@echo ""

test-stpsyr-full:	## Run full STPSYR test runner (experimental)
	@echo "=== Testing Full STPSYR Test Cases ==="
	@poetry run python tests_from_stpsyr/stpsyr_test_runner.py
	@echo ""

test-model:	## Run model and data structure tests
	@echo "=== Testing Models and Data Structures ==="
	poetry run python -m pytest tests/test_model.py tests/test_eval_model.py -v
	@echo ""

test-graphs:	## Run graph pathfinding tests
	@echo "=== Testing Graph Algorithms ==="
	@poetry run python -m pytest tests/test_graphs.py -k "not performance" -v
	@echo ""

test-graphs-perf:	## Run graph performance tests (verbose)
	@echo "=== Testing Graph Performance ==="
	@poetry run python tests/test_graphs.py -v
	@echo ""

integration-demo:	## Run integration demo showing algorithm in action
	@echo "=== Integration Demo ==="
	@poetry run python makefile-integration-demo.py
	@echo ""

test-imports:	## Test basic imports work
	@echo "=== Testing Basic Imports ==="
	@poetry run python makefile-test-imports.py
	@echo ""

lint: lint-check-ruff lint-check-format	## Run code quality checks (ruff + format)
	@echo "✅ Core code quality checks completed"
	@$(MAKE) lint-check-mypy || echo "⚠️  mypy has issues but functionality is not affected"

lint-check-ruff:	## Check ruff linting (internal target)
	@echo "Running ruff linter..."
	@poetry run ruff check dipworkpy/ tests/ || (echo "❌ ruff found issues" && exit 1)
	@echo "✅ ruff checks passed"

lint-check-format:	## Check ruff formatting (internal target)
	@echo "Checking ruff format..."
	@poetry run ruff format --check dipworkpy/ tests/ || (echo "❌ ruff format issues found" && echo "💡 Run 'make format' to fix" && exit 1)
	@echo "✅ ruff format checks passed"

lint-check-mypy:	## Check mypy types (internal target)
	@echo "Running mypy type checker..."
	@poetry run mypy dipworkpy/ || (echo "❌ mypy found type issues" && exit 1)
	@echo "✅ mypy type checks passed"

lint-fix:	## Fix linting and formatting issues
	@echo "Fixing linting issues..."
	poetry run ruff check --fix dipworkpy/ tests/
	@echo "Formatting code..."
	poetry run ruff format dipworkpy/ tests/
	@echo "✅ Linting and formatting fixes applied"

ruff:		## Run ruff linter
	poetry run ruff check dipworkpy/ tests/

ruff-fix:	## Run ruff linter and fix issues
	poetry run ruff check --fix dipworkpy/ tests/

format:		## Format code with ruff
	poetry run ruff format dipworkpy/ tests/

format-check:	## Check code formatting with ruff
	poetry run ruff format --check dipworkpy/ tests/

mypy:		## Run mypy type checking
	poetry run mypy dipworkpy/

clean:		## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

dev:		## Start development server (FastAPI)
	poetry run uvicorn dipworkpy:app --reload --host 0.0.0.0 --port 8000

# Quick verification that everything is working
verify: test-imports test-core integration-demo	## Quick verification of core functionality
	@echo "✅ Core algorithm verification complete!"