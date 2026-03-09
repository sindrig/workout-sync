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


## Task 2: XLS Parser Implementation

### xlrd Cell Types
- `xlrd.XL_CELL_DATE` (ctype=3) identifies date cells — primary filter for data rows vs summary/legend
- `xlrd.xldate_as_tuple(float_value, datemode)` returns (year, month, day, hour, min, sec) tuple
- Must cast `cell_value()` return to `float` explicitly for Pyright compatibility (type stubs return `str`)
- `xlrd.XL_CELL_NUMBER` (ctype=2) for numeric cells; empty cells have ctype=0

### XLS File Structure (Sindri Guðmunds - mars.xls)
- 61 rows, 6 columns; rows 0-7 are headers, rows 8-52 are data, rows 53-60 are legend
- Weekly summary rows: col0 ctype != 3, col2 contains "vikan X - Y" pattern — safely skipped by date check
- Empty separator rows between weeks: all ctypes=0 — safely skipped by date check
- Data spans 2026-03-09 to 2026-04-11 (5 weeks of training)

### Workout Type Classification Edge Cases
- **Classification order matters**: "jafnt" MUST be checked before "samæfing" because descriptions like "jafnt (ekki samæfing v/Skírdagur)" contain both keywords. The parenthetical "ekki samæfing" means "not samæfing" (negative context).
- Similarly "ról (ekki samæfing v/Annar í Páskum)" — "ról" checked first, correct.
- "Hlaupasería FH og Hlaupárs 5 km /eða samæf" — matches "samæfing" via truncated "samæf" substring. Also has "Hlaupasería" fallback rule but "samæf" catches it first.
- "hv eða styrktaræfing" (0km) — correctly kept as styrktaræfing (strength training, no running)
- Pure "hv" and "hv  " (with trailing spaces) — rest days, correctly filtered out

### Parsing Results
- 24 total workouts extracted from 35 day-rows (11 rest days filtered)
- Type breakdown: ról=13, samæfing=6, styrktaræfing=2, hraðaæf=2, jafnt=1
- No fartleikur or "other" types in this month's plan
- Description strings have trailing spaces from Excel — `.strip()` handles them

### Rest Day Filtering
- Rest = 0.0 km AND not styrktaræfing type
- 11 rest days filtered: pure "hv" entries on fös (Friday) and sun (Sunday)
- styrktaræfing entries on mið (Wednesday) kept despite 0km — these are strength training days

## Task 3: Garmin Workout JSON Builder

### Garmin Connect Workout JSON Schema (from real repos)
- Real Garmin API uses `ExecutableStepDTO` as `type` field (not `WorkoutStep`)
- Step types: `{"stepTypeId": 1, "stepTypeKey": "warmup"}`, `{"stepTypeId": 2, "stepTypeKey": "cooldown"}`, `{"stepTypeId": 3, "stepTypeKey": "interval"}`
- End conditions: `{"conditionTypeId": 3, "conditionTypeKey": "distance"}` for distance, `{"conditionTypeId": 1, "conditionTypeKey": "lap.button"}` for lap press, `{"conditionTypeId": 2, "conditionTypeKey": "time"}` for time
- Distance values are in meters (float), time in seconds
- Pace targets use `{"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"}` with m/s values
- No target: `{"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}`
- Sport types: running=1, cycling=2, strength_training=4
- Segment structure: always 1 segment with segmentOrder=1

### Key repos for Garmin workout JSON reference
- `Taxuspt/garmin_mcp` — Most complete examples of workout templates with real Garmin API format
- `st3v/garmin-workouts-mcp` — Has STEP_TYPE_MAPPING, END_CONDITION_TYPE_MAPPING (comprehensive ID lookups)
- `mkuthan/garmin-workouts` — Python models for cycling workouts with RepeatGroupDTO
- `cyberjunky/python-garminconnect` — `upload_workout()` just POST the JSON dict to Garmin API endpoint

### Pace Conversion Formula
- Input: "M:SS" per km → Output: (low_ms, high_ms) in meters/second
- ±10 sec tolerance: slower pace (more sec/km) = lower m/s = targetValueOne; faster = higher m/s = targetValueTwo
- Example: "5:15" → slow=5:25=325s/km=3.08m/s, fast=5:05=305s/km=3.28m/s

### Builder Design Decisions
- Used simplified schema fields (intensity, durationType, targetType as strings) per task spec rather than full DTO format
- Future integration: may need to map to ExecutableStepDTO format for actual Garmin API upload
- Edge case handling: when total distance < warmup+cooldown, proportionally scale down (no negative distances)
- Zero-distance edge: 1km ról results in 500m warmup + 500m cooldown (no active step)
- Workout type dispatch via STEP_TEMPLATES dict + PACE_TARGETS dict, clean separation

### Workout Type Step Templates (implemented)
- ról: 1km warmup | active @ 5:15/km | 1km cooldown
- samæfing: 2km warmup | active no target | 2km cooldown
- hraðaæf: 2.5km warmup | active INTERVAL | 2km cooldown
- jafnt: 1km warmup | active @ 4:50/km | 1km cooldown
- styrktaræfing: strength_training sport, single LAP_BUTTON_PRESS step
- fartleikur: 2km warmup | active no target | 2km cooldown
- other: single active step, full distance, no target

## Task 4: Garmin Connect Client

### python-garminconnect API Surface
- `Garmin(email, password, prompt_mfa=callable)` — constructor, prompt_mfa called if MFA required
- `client.login(tokenstore=path)` — loads tokens from dir, or logs in with credentials
- `client.garth.dump(dir)` — saves OAuth tokens to directory for next session
- `client.get_workouts(start=0, limit=100)` — returns list of workout dicts (typed as dict but is actually list)
- `client.upload_workout(json_dict)` — POSTs to /workout-service/workout, returns dict with workoutId
- No built-in schedule_workout or delete_workout — use garth directly

### Schedule Endpoint (from mkuthan/garmin-workouts)
- `POST /workout-service/schedule/{workout_id}` with body `{"date": "YYYY-MM-DD"}`
- Via garth: `client.garth.post("connectapi", url, json=payload, api=True)`
- Required headers (Referer, nk: NT) handled internally by garth's api=True flag

### Delete Endpoint
- `DELETE /workout-service/workout/{workout_id}`
- Via garth: `client.garth.request("DELETE", "connectapi", url, api=True)`
- Same pattern used by python-garminconnect's own delete_activity method

### Token Caching
- garth saves OAuth1 + OAuth2 tokens to ~/.garth as JSON files
- `garth.Client.load(path)` / `garth.Client.dump(path)` for persistence
- Strategy: try loading cached tokens, catch any exception, fall back to fresh login

### LSP Environment Note
- Pyright can't resolve `garminconnect` import (reportMissingImports) — false positive from venv resolution
- Runtime import works fine via `uv run python -c "from workout_sync.garmin_client import GarminClient"`
