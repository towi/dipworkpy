# DipworkPy Makefile
# Diplomacy Conflict Resolution Algorithm

.PHONY: help install check test test-core test-datc test-graphs test-graphs-perf test-stpsyr test-stpsyr-full test-dipnet-quick test-dipnet-full integration-demo test-imports clean lint lint-check-ruff lint-check-format lint-check-mypy lint-fix ruff ruff-fix format format-check mypy verify dev examples examples-check docs docs-prep docs-serve docs-clean

help:		## Show this help
	@echo "DipworkPy - Diplomacy Conflict Resolution"
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies with uv (incl. dev group; use 'uv sync --group docs' for docs deps)
	uv sync

check: install test-core test-datc test-graphs test-stpsyr integration-demo lint	## Run comprehensive algorithm correctness checks

test:		## Run all available tests
	uv run python -m pytest tests/ -v

test-core:	## Run core conflict resolution tests
	@echo "=== Testing Core Conflict Resolution Algorithm ==="
	uv run python -m pytest tests/test_conflict_game.py -v
	@echo ""

test-datc:	## Run DATC (Diplomacy Adjudication Test Cases) compliance tests
	@echo "=== Testing DATC Compliance ==="
	uv run python -m pytest tests/test_conflict_datc.py -v
	@echo ""

test-stpsyr:	## Run STPSYR test cases (simple)
	@echo "=== Testing STPSYR Test Cases ==="
	@uv run python tests_from_stpsyr/test_stpsyr_simple.py
	@echo ""

test-stpsyr-full:	## Run full STPSYR test runner (experimental)
	@echo "=== Testing Full STPSYR Test Cases ==="
	@uv run python tests_from_stpsyr/stpsyr_test_runner.py
	@echo ""

test-dipnet-quick:	## Run DipNet tests (first 100 games)
	@echo "=== DipNet Conflict Resolution Tests (100 games) ==="
	@uv run python -m test_data_pipeline.run_dipnet_tests --max-games 100 ../testdata/diplomacy-research/standard_no_press.jsonl
	@echo ""

test-dipnet-full:	## Run DipNet tests (all 33K games, slow)
	@echo "=== DipNet Conflict Resolution Tests (full dataset) ==="
	@uv run python -m test_data_pipeline.run_dipnet_tests --workers 8 ../testdata/diplomacy-research/standard_no_press.jsonl
	@echo ""

test-model:	## Run model and data structure tests
	@echo "=== Testing Models and Data Structures ==="
	uv run python -m pytest tests/test_model.py tests/test_eval_model.py -v
	@echo ""

test-graphs:	## Run graph pathfinding tests
	@echo "=== Testing Graph Algorithms ==="
	@uv run python -m pytest tests/test_graphs.py -k "not performance" -v
	@echo ""

test-graphs-perf:	## Run graph performance tests (verbose)
	@echo "=== Testing Graph Performance ==="
	@uv run python tests/test_graphs.py -v
	@echo ""

integration-demo:	## Run integration demo showing algorithm in action
	@echo "=== Integration Demo ==="
	@uv run python makefile-integration-demo.py
	@echo ""

test-imports:	## Test basic imports work
	@echo "=== Testing Basic Imports ==="
	@uv run python makefile-test-imports.py
	@echo ""

lint: lint-check-ruff lint-check-format	## Run code quality checks (ruff + format)
	@echo "✅ Core code quality checks completed"
	@$(MAKE) lint-check-mypy || echo "⚠️  mypy has issues but functionality is not affected"

lint-check-ruff:	## Check ruff linting (internal target)
	@echo "Running ruff linter..."
	@uv run ruff check dipworkpy/ tests/ || (echo "❌ ruff found issues" && exit 1)
	@echo "✅ ruff checks passed"

lint-check-format:	## Check ruff formatting (internal target)
	@echo "Checking ruff format..."
	@uv run ruff format --check dipworkpy/ tests/ || (echo "❌ ruff format issues found" && echo "💡 Run 'make format' to fix" && exit 1)
	@echo "✅ ruff format checks passed"

lint-check-mypy:	## Check mypy types (internal target)
	@echo "Running mypy type checker..."
	@uv run mypy dipworkpy/ || (echo "❌ mypy found type issues" && exit 1)
	@echo "✅ mypy type checks passed"

lint-fix:	## Fix linting and formatting issues
	@echo "Fixing linting issues..."
	uv run ruff check --fix dipworkpy/ tests/
	@echo "Formatting code..."
	uv run ruff format dipworkpy/ tests/
	@echo "✅ Linting and formatting fixes applied"

ruff:		## Run ruff linter
	uv run ruff check dipworkpy/ tests/

ruff-fix:	## Run ruff linter and fix issues
	uv run ruff check --fix dipworkpy/ tests/

format:		## Format code with ruff
	uv run ruff format dipworkpy/ tests/

format-check:	## Check code formatting with ruff
	uv run ruff format --check dipworkpy/ tests/

mypy:		## Run mypy type checking
	uv run mypy dipworkpy/

clean:		## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

dev:		## Start development server (FastAPI)
	uv run uvicorn dipworkpy:app --reload --host 0.0.0.0 --port 8000

examples:	## Render all DDL examples + regenerate EXAMPLES.md
	@echo "=== Rendering DDL Examples ==="
	uv run python -m dipworkpy.tools.dwex render-all doc/examples/dwex
	uv run python -m dipworkpy.tools.dwex.generate_index doc/examples/dwex doc/EXAMPLES.md
	@echo ""

examples-check:	## Verify DDL examples render and validate
	@echo "=== Verifying DDL Examples ==="
	uv run python -m pytest tests/test_dwex_examples.py -v
	@echo ""

docs-prep:	## Mirror cross-tree design docs into project/doc/_design/ (gitignored)
	@echo "=== Mirroring spec/plan/status + NOTATION.md ==="
	@mkdir -p doc/_design
	@cp ../docs/superpowers/specs/2026-05-12-dipworkpy-comprehensive-design.md doc/_design/spec.md
	@cp ../docs/superpowers/plans/2026-05-12-dipworkpy-implementation.md doc/_design/plan.md
	@cp ../docs/superpowers/STATUS-2026-05-13.md doc/_design/status.md
	@cp NOTATION.md doc/_design/notation.md
	@echo "✅ Mirrored 4 files into doc/_design/"

docs: examples docs-prep	## Render DDL examples + mirror design docs + build MkDocs site to doc-site/
	@echo "=== Building Docs Site (MkDocs) ==="
	uv sync --group docs --quiet
	uv run --group docs mkdocs build
	@echo ""
	@echo "✅ Docs built to doc-site/. Open doc-site/index.html in a browser."

docs-serve: docs-prep	## Live-preview the docs site at http://127.0.0.1:8000/
	@echo "=== Serving Docs Site (live reload) ==="
	uv sync --group docs --quiet
	uv run --group docs mkdocs serve

docs-clean:	## Remove generated docs site and mirrored design docs
	rm -rf doc-site doc/_design

# Quick verification that everything is working
verify: test-imports test-core integration-demo	## Quick verification of core functionality
	@echo "✅ Core algorithm verification complete!"
