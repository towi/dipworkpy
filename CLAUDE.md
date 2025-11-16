# dipworkpy - Claude Code Configuration

## Project Overview
Diplomacy Conflict Solver and game server (re)written in Python

## Project Structure
- `project/dipworkpy/` - Main source code directory
- `project/dipworkpy/model.py` - Core data models using Pydantic
- `project/dipworkpy/conflict_game.py` - Game logic implementation
- `project/dipworkpy/graphs.py` - Graph-related functionality
- `project/dipworkpy/dip_eval/` - Evaluation modules
- `project/playground/` - Testing and experimental code
- `pas/SOURCE/` - Original Pascal reference implementation (proven in practice)
- `pas/DIPPY20/` - Real-world runtime config for Pascal version

## Key Technologies
- Python
- Pydantic for data models
- Enum for type definitions

## Development Commands
- `make help` - Show available commands
- `make check` - Run comprehensive algorithm correctness checks + linting (RECOMMENDED)
- `make install` - Install dependencies with Poetry
- `make test-core` - Run core conflict resolution tests
- `make test-datc` - Run DATC compliance tests
- `make integration-demo` - Run live algorithm demonstration
- `make verify` - Quick verification of core functionality
- `make lint` - Run code quality checks (ruff + mypy)
- `make lint-fix` - Auto-fix linting and formatting issues
- `make ruff` - Run ruff linter only
- `make format` - Format code with ruff
- `make mypy` - Run mypy type checking only
- `make dev` - Start FastAPI development server

## Notes
- This is a Diplomacy board game conflict resolution system
- Uses strategic game theory concepts
- Legacy codebase with mixed maintenance status (see badges in README)
- Pascal source code in `pas/SOURCE/` serves as reference implementation for conflict resolution algorithm
- See `project/NOTATION.md` for detailed documentation of the Diplomacy notation system used
- See `project/TEST_CASES_DATC.md` for DATC test cases in DipworkPy notation
