# Makefile Helper Scripts

This directory contains Python scripts that support the Makefile targets, keeping Python code separate from the Makefile itself for better maintainability.

## Files

- **`makefile-test-imports.py`** - Tests basic module imports and model creation
- **`makefile-integration-demo.py`** - Live demonstration of the conflict resolution algorithm

## Usage

These scripts are called automatically by the Makefile:

```bash
make test-imports      # Runs makefile-test-imports.py
make integration-demo  # Runs makefile-integration-demo.py
make lint             # Integrated linting (ruff + mypy) using pure Makefile rules
make check            # Runs comprehensive checks including all above
```

## Direct Usage

You can also run these scripts directly:

```bash
poetry run python makefile-test-imports.py
poetry run python makefile-integration-demo.py
```

## Script Details

### makefile-test-imports.py
- Verifies basic dipworkpy imports work
- Tests Order model creation
- Returns exit code 0 for success, 1 for failure

### makefile-integration-demo.py
- Demonstrates bounce scenario (two units attacking same territory)
- Demonstrates convoy scenario (complex multi-unit interaction)
- Shows live algorithm results

## Linting Integration

Code quality checks (ruff + mypy) are now integrated directly into the Makefile using standard make tools:

- `make lint` - Run all quality checks
- `make lint-check-ruff` - Run ruff linting only
- `make lint-check-format` - Check code formatting only
- `make lint-check-mypy` - Run mypy type checking only
- `make lint-fix` - Auto-fix linting and formatting issues

This approach eliminates the need for a separate Python script while providing better error handling and integration with the build system.