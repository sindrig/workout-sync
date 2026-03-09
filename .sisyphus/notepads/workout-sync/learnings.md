# Learnings — Workout Sync

## Conventions

## Patterns

## Gotchas
# Workout Sync Learnings

## Task 1: Project Scaffolding

### uv Project Initialization
- `uv init --name workout-sync` creates a standard Python project structure
- Initial pyproject.toml has minimal configuration (name, version, description, requires-python, dependencies)
- Script entry points require `[project.scripts]` section in pyproject.toml format: `script-name = "module.path:function"`

### Dependency Installation
- `uv add <package>` correctly resolves package names from PyPI
- Package names may differ from GitHub repo names (e.g., PyPI: `garminconnect`, not `python-garminconnect`)
- All three dependencies installed successfully with transitive dependencies:
  - garminconnect 0.2.38 (with garth, requests, oauthlib, pydantic)
  - xlrd 2.0.2
  - python-dotenv 1.2.2

### Package Structure
- Python packages require `__init__.py` in the package directory
- `__main__.py` enables `python -m package_name` execution
- Placeholder implementations work fine for scaffolding; no actual logic needed yet

### CLI Implementation
- argparse handles `--help` automatically; don't manually add it to parser
- `ArgumentParser(prog="name")` sets the command name in help output
- Exit point: `parser.parse_args()` triggers help display or raises errors

### Module Entry Points
- Script entry point syntax: `"workout-sync = "workout_sync.cli:main"` (module path then function name)
- uv sync warning about missing entry points is expected for non-packaged projects during dev
- Entry points work via `uv run python -m workout_sync` even without installation

### .env Configuration
- `.env.example` serves as template; actual `.env` should not be committed
- Standard format: `KEY=value` with clear placeholder values
- Both GARMIN_EMAIL and GARMIN_PASSWORD templates created successfully

### Testing & Verification
- `uv sync` should complete without errors even with entry point warnings
- `uv run python -m workout_sync --help` confirms CLI integration working
- All file structure verified: 6 modules + 2 config files created

### Next Steps for Future Tasks
- Parser module will handle XLS/XLSX parsing (use xlrd, openpyxl)
- Builder module will construct objects from parsed data
- GarminClient will integrate with garminconnect library
- CLI will orchestrate the complete workflow

