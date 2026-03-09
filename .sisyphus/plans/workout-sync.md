# Workout Sync CLI — XLS → Garmin Connect

## TL;DR

> **Quick Summary**: Python CLI tool that parses a coach-made XLS workout plan (Icelandic running training) and uploads structured workouts with warmup/cooldown steps and pace targets to the Garmin Connect training calendar.
> 
> **Deliverables**:
> - `workout_sync/` Python package with CLI entry point
> - XLS parser for the coach's exact format (Hlaupasamfélagið)
> - Garmin workout builder with structured steps (warmup/main/cooldown)
> - Garmin Connect uploader with calendar scheduling
> - `--dry-run` mode for preview without uploading
> 
> **Estimated Effort**: Short (4-6 focused tasks)
> **Parallel Execution**: YES — 2 waves
> **Critical Path**: Task 1 (scaffold) → Task 2 (parser) → Task 3 (workout builder) → Task 4 (Garmin client) → Task 5 (CLI glue) → Task 6 (QA)

---

## Context

### Original Request
Build a simple CLI tool to parse an XLS workout plan and upload workouts to Garmin Connect's training calendar. Personal use only, no UI, no bloat.

### Interview Summary
**Key Discussions**:
- XLS format analyzed: Coach's plan from Hlaupasamfélagið with Icelandic workout types (ról, samæfing, hraðaæf, jafnt, styrktaræfing, fartleikur), dates as Excel serials, 6 columns
- Garmin API: python-garminconnect + garth for auth, reverse-engineered endpoints (no official API needed)
- Structured workouts preferred: warmup/main/cooldown steps with pace targets from coach's legend
- Wipe-and-reupload idempotency strategy
- Rest days (hv/0km) skipped entirely
- Python with uv, env vars for credentials

**Research Findings**:
- python-garminconnect (1,849★) has `upload_workout()`, garth handles OAuth1 with ~1yr token persistence
- mkuthan/garmin-workouts shows `schedule_workout(workout_id, date)` implementation
- Garmin workout JSON: sportType, workoutSegments, workoutSteps with intensity/duration/target types
- Go ecosystem dead for Garmin — Python is the only viable option

### Metis Review
**Self-identified gaps** (addressed):
- Edge case: workouts with 0km but not "hv" (styrktaræfing) → handled as strength training, no distance
- Pace target format for Garmin API → needs conversion from min:sec/km to m/s (Garmin uses metric speed internally)
- "Wipe" scope: what counts as "our" workouts to delete → use workout name prefix to identify tool-created workouts
- Error handling for Garmin API failures mid-upload → log and continue, report summary at end
- Token refresh flow → garth handles automatically, but initial login must handle MFA if enabled

---

## Work Objectives

### Core Objective
Parse the coach's XLS training plan and upload each workout day as a structured Garmin Connect workout scheduled on the correct calendar date.

### Concrete Deliverables
- `workout_sync/parser.py` — XLS parsing module
- `workout_sync/builder.py` — Garmin workout JSON builder
- `workout_sync/garmin_client.py` — Garmin Connect API client (upload + schedule + delete)
- `workout_sync/cli.py` — CLI entry point with argparse
- `workout_sync/__init__.py` + `pyproject.toml` — Package setup
- `.env.example` — Credential template

### Definition of Done
- [ ] `python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls` prints parsed workouts correctly
- [ ] `python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls` uploads workouts to Garmin Connect calendar
- [ ] Re-running the tool deletes previous uploads and re-uploads cleanly
- [ ] Workouts appear on Garmin Connect calendar on the correct dates with structured steps

### Must Have
- Parse all non-rest workout days from XLS
- Structured workout steps (warmup/main/cooldown) per workout type
- Pace targets for ról (~5:15/km) and jafnt (~4:50/km)
- Schedule each workout on its correct calendar date
- --dry-run flag for preview
- Wipe-and-reupload: delete previous tool-created workouts before uploading
- Error handling: don't crash on single workout failure, log and continue

### Must NOT Have (Guardrails)
- NO web server, no Flask, no FastAPI
- NO database or persistent state beyond garth token cache
- NO flexible/generic XLS parser — hardcoded to this exact format
- NO over-engineered abstractions (no factory patterns, no plugin systems)
- NO activity upload (this is about future workout PLANS, not past activities)
- NO GUI or TUI — plain stdout output
- NO excessive comments or docstrings — code should be self-explanatory
- NO typing overkill — use types where helpful, skip where obvious

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (greenfield project)
- **Automated tests**: None
- **Framework**: N/A
- **Verification**: Agent-executed QA scenarios (dry-run output checks + Garmin API verification)

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI output**: Use Bash — run command, validate stdout output
- **XLS parsing**: Use Bash — run dry-run, compare output against known XLS content
- **Garmin upload**: Use Bash — run upload, then use python-garminconnect to query calendar and verify workouts exist

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation):
├── Task 1: Project scaffolding (pyproject.toml, uv, package structure) [quick]
├── Task 2: XLS parser module [unspecified-high]
└── Task 3: Garmin workout JSON builder [unspecified-high]

Wave 2 (After Wave 1 — integration):
├── Task 4: Garmin Connect client (auth + upload + schedule + delete) [deep]
└── Task 5: CLI entry point (argparse + glue logic + dry-run) [quick]

Wave 3 (After Wave 2 — verification):
└── Task 6: End-to-end QA [deep]

Wave FINAL (After ALL tasks):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1 → Task 2 → Task 4 → Task 5 → Task 6 → F1-F4
Parallel Speedup: Tasks 2+3 run in parallel, F1-F4 run in parallel
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 2, 3, 4, 5 |
| 2 | 1 | 5, 6 |
| 3 | 1 | 4, 5 |
| 4 | 1, 3 | 5, 6 |
| 5 | 2, 3, 4 | 6 |
| 6 | 5 | F1-F4 |
| F1-F4 | 6 | — |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `unspecified-high`, T3 → `unspecified-high`
- **Wave 2**: 2 tasks — T4 → `deep`, T5 → `quick`
- **Wave 3**: 1 task — T6 → `deep`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Project Scaffolding

  **What to do**:
  - Initialize uv project: `uv init` or create `pyproject.toml` manually
  - Add dependencies: `python-garminconnect`, `xlrd`, `python-dotenv`
  - Create package structure:
    ```
    workout_sync/
      __init__.py
      __main__.py  (entry point: from .cli import main; main())
      parser.py
      builder.py
      garmin_client.py
      cli.py
    .env.example   (GARMIN_EMAIL=, GARMIN_PASSWORD=)
    pyproject.toml
    ```
  - Set up `pyproject.toml` with `[project.scripts]` entry: `workout-sync = "workout_sync.cli:main"`
  - Verify `uv run python -m workout_sync --help` works (even if it just prints "not implemented")

  **Must NOT do**:
  - Don't add test frameworks, CI configs, or Docker
  - Don't add unnecessary dependencies
  - Don't create README or docs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple scaffolding task, no complex logic
  - **Skills**: []
    - No special skills needed for file creation

  **Parallelization**:
  - **Can Run In Parallel**: NO (must be first)
  - **Parallel Group**: Wave 1 (runs first, blocks all others)
  - **Blocks**: Tasks 2, 3, 4, 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - No existing code in repo (greenfield)

  **External References**:
  - uv docs: https://docs.astral.sh/uv/ — project init and dependency management
  - python-garminconnect PyPI: `pip install garminconnect` — verify package name

  **WHY Each Reference Matters**:
  - uv docs needed for correct pyproject.toml format and `uv add` syntax
  - Package name on PyPI may differ from GitHub repo name

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Project structure exists and dependencies resolve
    Tool: Bash
    Preconditions: Clean repo with only .git
    Steps:
      1. Run `ls workout_sync/` and verify all 6 .py files exist
      2. Run `cat pyproject.toml` and verify dependencies listed
      3. Run `uv sync` and verify it completes without errors
      4. Run `uv run python -m workout_sync --help` and verify it produces output (even placeholder)
    Expected Result: All files exist, deps install, entry point runs
    Failure Indicators: Missing files, uv sync fails, import errors
    Evidence: .sisyphus/evidence/task-1-scaffold.txt

  Scenario: .env.example contains expected variables
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Run `cat .env.example`
      2. Verify it contains GARMIN_EMAIL and GARMIN_PASSWORD placeholders
    Expected Result: File contains both env var templates
    Failure Indicators: File missing or wrong variable names
    Evidence: .sisyphus/evidence/task-1-env-example.txt
  ```

  **Commit**: YES
  - Message: `feat: scaffold project with uv and package structure`
  - Files: `pyproject.toml, workout_sync/*.py, .env.example`
  - Pre-commit: `uv run python -m workout_sync --help`

- [x] 2. XLS Parser Module

  **What to do**:
  - Implement `workout_sync/parser.py`
  - Define a `Workout` dataclass:
    ```python
    @dataclass
    class Workout:
        date: datetime.date
        day_name: str          # Icelandic day abbreviation (mán, þri, etc.)
        workout_type: str      # ról, samæfing, hraðaæf, jafnt, styrktaræfing, fartleikur
        description: str       # Full description from XLS
        distance_km: float     # Planned km
        notes: str             # Notes column
    ```
  - Implement `parse_xls(filepath: str) -> list[Workout]`:
    - Open with `xlrd.open_workbook(filepath)`
    - Use sheet index 0
    - Iterate rows starting from row 8
    - Skip rows where date cell ctype != 3 (skip weekly summaries, blanks, legend)
    - Skip rows where distance_km == 0.0 AND workout_type is not "styrktaræfing" (skip rest days)
    - Decode dates with `xlrd.xldate_as_tuple(cell.value, wb.datemode)`
    - Classify workout type from description text:
      - Contains "ról" → type "ról" (also matches "ról" at start of description)
      - Contains "samæfing" → type "samæfing"
      - Contains "hraðaæf" → type "hraðaæf"
      - Contains "jafnt" → type "jafnt"
      - Contains "styrktaræfing" → type "styrktaræfing"
      - Contains "fartleikur" or "fartleik" → type "fartleikur"
      - Contains "Hlaupasería" → type "samæfing" (race series = group event)
      - Fallback: type "other"
    - Return sorted list of Workouts by date

  **Must NOT do**:
  - Don't make the parser generic/configurable
  - Don't use pandas (overkill for this simple structure)
  - Don't try to parse the legend or header rows

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core parsing logic with specific format handling and Icelandic text classification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1 — but depends on Task 1 for package structure)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - XLS file: `~/Downloads/Sindri Guðmunds - mars.xls` — the actual input file to parse

  **External References**:
  - xlrd docs: `xlrd.open_workbook()`, `sheet.cell(row, col)`, cell.ctype values (0=empty, 2=number, 3=date), `xlrd.xldate_as_tuple()`

  **WHY Each Reference Matters**:
  - The XLS file IS the spec — parser must match its exact structure
  - xlrd ctype=3 is critical for identifying date rows vs summary/legend rows

  **XLS Structure Reference** (from analysis):
  ```
  Row 0-7: Header (skip)
  Row 8+: Data rows — 6 columns:
    Col 0: Date (ctype=3, Excel serial number)
    Col 1: Day abbreviation (mán/þri/mið/fim/fös/lau/sun)
    Col 2: Workout description (Icelandic)
    Col 3: Planned km (float)
    Col 4: Actual km (float, usually empty)
    Col 5: Notes (string)
  Weekly summary rows: Col 0 empty, Col 2 contains "vikan X - Y"
  Rows 53-60: Legend (no date cell)
  ```

  **Known workout entries** (for QA validation):
  ```
  2026-03-09 (mán): samæfing í Kaplakrika kl 18:00      | 9.0 km  | með upph og niðursk
  2026-03-10 (þri): ról                                   | 10.0 km |
  2026-03-14 (lau): ról                                   | 16.0 km |
  2026-03-23 (mán): hraðaæf frá Laugardalslaug 17:30     | 10.0 km | með upph og niðursk
  2026-04-02 (fim): jafnt  (ekki samæfing v/Skírdagur)   | 10.0 km |
  ```

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Parse all workouts from the XLS file
    Tool: Bash
    Preconditions: Task 1 complete, XLS file at ~/Downloads/Sindri Guðmunds - mars.xls
    Steps:
      1. Run `uv run python -c "from workout_sync.parser import parse_xls; workouts = parse_xls('$HOME/Downloads/Sindri Guðmunds - mars.xls'); [print(f'{w.date} ({w.day_name}): {w.workout_type} - {w.description} | {w.distance_km} km') for w in workouts]"`
      2. Count output lines — should be approximately 22-25 (non-rest days across 5 weeks)
      3. Verify first entry is 2026-03-09, type "samæfing", 9.0 km
      4. Verify rest days (hv, 0km) are NOT present in output
      5. Verify 2026-04-02 is type "jafnt"
      6. Verify 2026-03-23 is type "hraðaæf"
    Expected Result: All non-rest workouts parsed with correct dates, types, distances
    Failure Indicators: Wrong dates, missing workouts, rest days appearing, wrong type classification
    Evidence: .sisyphus/evidence/task-2-parse-all.txt

  Scenario: Rest days are excluded
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Run parse and grep for "hv" in output
      2. Run parse and check no entries have 0.0 km (except strength training)
    Expected Result: Zero rest day entries in parsed output
    Failure Indicators: Any "hv" entries or 0.0 km non-strength entries
    Evidence: .sisyphus/evidence/task-2-no-rest-days.txt
  ```

  **Commit**: YES (groups with Task 3 if in same wave)
  - Message: `feat: add XLS parser with workout type classification`
  - Files: `workout_sync/parser.py`
  - Pre-commit: `uv run python -c "from workout_sync.parser import parse_xls; print('OK')"`

- [x] 3. Garmin Workout JSON Builder

  **What to do**:
  - Implement `workout_sync/builder.py`
  - Create function `build_workout_json(workout: Workout) -> dict` that converts a parsed Workout to Garmin's JSON format
  - Workout name format: `[WS] {description}` (prefix `[WS]` = Workout Sync, used for identifying our workouts during wipe)
  - Implement structured steps for each workout type:

  **ról (easy run)**:
  ```python
  steps = [
      warmup_step(distance_km=1.0),
      active_step(distance_km=workout.distance_km - 2.0, pace_target="5:15"),
      cooldown_step(distance_km=1.0),
  ]
  ```

  **samæfing (group training)**:
  ```python
  steps = [
      warmup_step(distance_km=2.0),
      active_step(distance_km=workout.distance_km - 4.0),  # no specific pace target
      cooldown_step(distance_km=2.0),
  ]
  ```

  **hraðaæf (speed work)**:
  ```python
  steps = [
      warmup_step(distance_km=2.5),
      active_step(distance_km=workout.distance_km - 4.5, intensity="INTERVAL"),
      cooldown_step(distance_km=2.0),
  ]
  ```

  **jafnt (steady)**:
  ```python
  steps = [
      warmup_step(distance_km=1.0),
      active_step(distance_km=workout.distance_km - 2.0, pace_target="4:50"),
      cooldown_step(distance_km=1.0),
  ]
  ```

  **styrktaræfing (strength)**:
  ```python
  # Different sport type, no distance, open-ended
  sport_type = {"sportTypeId": 4, "sportTypeKey": "strength_training"}
  steps = [active_step_open()]  # LAP_BUTTON_PRESS duration
  ```

  **fartleikur (fartlek)**:
  ```python
  steps = [
      warmup_step(distance_km=2.0),
      active_step(distance_km=workout.distance_km - 4.0),  # fartlek = variable pace
      cooldown_step(distance_km=2.0),
  ]
  ```

  **other (fallback)**:
  ```python
  # Simple single-step workout
  steps = [active_step(distance_km=workout.distance_km)]
  ```

  - Pace targets: Convert min:sec/km to Garmin's format
    - Garmin uses meters/second for pace targets internally
    - 5:15/km = 315 seconds/km. For Garmin `targetValueOne`/`targetValueTwo`, research exact format from python-garminconnect source or mkuthan/garmin-workouts
    - Provide a range: e.g., 5:15/km target → 5:05-5:25/km range
  - Helper functions: `warmup_step(distance_km)`, `active_step(distance_km, pace_target=None, intensity="ACTIVE")`, `cooldown_step(distance_km)`
  - Each step is a dict matching Garmin's workoutStep schema:
    ```python
    {
        "type": "WorkoutStep",
        "stepOrder": N,
        "intensity": "WARMUP" | "ACTIVE" | "COOLDOWN",
        "durationType": "DISTANCE",
        "durationValue": distance_in_meters,
        "targetType": "PACE" | "NO_TARGET",
        "targetValueOne": low_pace_m_per_s,  # if pace target
        "targetValueTwo": high_pace_m_per_s,  # if pace target
    }
    ```
  - Full workout JSON structure:
    ```python
    {
        "workoutName": "[WS] description",
        "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
            "workoutSteps": [step1, step2, step3]
        }]
    }
    ```

  **Must NOT do**:
  - Don't implement workout types not in the XLS (swimming, cycling, etc.)
  - Don't over-engineer pace conversion — simple function is fine
  - Don't add configurable pace targets — hardcode from coach's legend

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding Garmin's workout JSON schema and correct pace conversion
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2, after Task 1)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - python-garminconnect source: `upload_workout()` method — shows expected JSON format
  - mkuthan/garmin-workouts sample workouts: https://github.com/mkuthan/garmin-workouts/tree/master/sample_workouts — YAML workout definitions showing step structure

  **API/Type References**:
  - Garmin workout step schema: intensity values (WARMUP, ACTIVE, COOLDOWN, REST, INTERVAL), durationType values (DISTANCE, TIME, LAP_BUTTON_PRESS), targetType values (PACE, HEART_RATE, NO_TARGET)
  - sportTypeId: 1=running, 4=strength_training

  **External References**:
  - python-garminconnect GitHub: https://github.com/cyberjunky/python-garminconnect — check `upload_running_workout` for Pydantic model showing exact field names
  - mkuthan/garmin-workouts: https://github.com/mkuthan/garmin-workouts — `garminworkouts/models/` for workout JSON structure reference

  **WHY Each Reference Matters**:
  - The Garmin API is undocumented — these open source projects are the only reference for correct JSON field names and values
  - Pace target format (m/s vs sec/km vs sec/m) must match what Garmin expects — get it wrong and the workout either errors or shows wrong pace

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Build structured workout JSON for each type
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Run `uv run python -c "
         from workout_sync.parser import Workout
         from workout_sync.builder import build_workout_json
         from datetime import date
         import json
         w = Workout(date=date(2026,3,10), day_name='þri', workout_type='ról', description='ról', distance_km=10.0, notes='')
         result = build_workout_json(w)
         print(json.dumps(result, indent=2))
         "`
      2. Verify JSON has workoutName starting with "[WS]"
      3. Verify workoutSegments has 3 workoutSteps (warmup, active, cooldown)
      4. Verify warmup step has intensity "WARMUP" and distance 1000m
      5. Verify active step has pace target values set
      6. Verify cooldown step has intensity "COOLDOWN" and distance 1000m
    Expected Result: Valid Garmin workout JSON with 3 structured steps and pace targets
    Failure Indicators: Missing steps, wrong intensity values, no pace targets for ról
    Evidence: .sisyphus/evidence/task-3-rol-workout.json

  Scenario: Strength training uses different sport type
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Build workout JSON for styrktaræfing type
      2. Verify sportTypeKey is "strength_training"
      3. Verify no distance-based steps (uses LAP_BUTTON_PRESS or open)
    Expected Result: Strength workout with correct sport type and no distance targets
    Failure Indicators: Running sport type, distance-based steps
    Evidence: .sisyphus/evidence/task-3-strength-workout.json

  Scenario: Edge case — workout with small distance (e.g., 5km ról)
    Tool: Bash
    Preconditions: Task 1 complete
    Steps:
      1. Build workout JSON for ról with 5.0 km (1km warmup + 3km active + 1km cooldown)
      2. Verify active step distance is 3000m (not negative)
    Expected Result: All step distances positive, sum equals total
    Failure Indicators: Negative distance, steps don't sum to total
    Evidence: .sisyphus/evidence/task-3-small-distance.json
  ```

  **Commit**: YES (groups with Task 2)
  - Message: `feat: add Garmin workout JSON builder with structured steps`
  - Files: `workout_sync/builder.py`
  - Pre-commit: `uv run python -c "from workout_sync.builder import build_workout_json; print('OK')"`

- [x] 4. Garmin Connect Client (Auth + Upload + Schedule + Delete)

  **What to do**:
  - Implement `workout_sync/garmin_client.py`
  - Class `GarminClient`:
    ```python
    class GarminClient:
        def __init__(self, email: str, password: str):
            # Initialize garminconnect.Garmin client
            # Login and handle token caching via garth

        def login(self):
            # Try resuming from ~/.garth first
            # If no cached session, login with email/password
            # Handle MFA prompt if needed (print code to terminal, read input)

        def delete_workouts_by_prefix(self, prefix: str = "[WS]"):
            # Fetch all workouts (GET /workout-service/workouts)
            # Filter by name starting with prefix
            # Delete each one (DELETE /workout-service/workout/{id})
            # Print count of deleted workouts

        def upload_and_schedule(self, workout_json: dict, date: str) -> dict:
            # POST workout JSON → get workout_id
            # POST schedule with workout_id + date
            # Return result with workout_id and schedule status

        def upload_all(self, workouts: list[tuple[dict, str]]):
            # For each (workout_json, date_str):
            #   Try upload_and_schedule
            #   On failure: log error, continue to next
            # Print summary: N uploaded, M failed
    ```
  - Use `python-garminconnect`'s `Garmin` class for auth and API calls
  - For scheduling (not in python-garminconnect), use garth directly:
    ```python
    self.client.garth.post(
        "connectapi",
        f"/workout-service/schedule/{workout_id}",
        json={"date": date_str},
        api=True
    )
    ```
  - Token persistence: garth saves to `~/.garth` by default
  - Required headers for schedule endpoint: `{"Referer": "https://connect.garmin.com/modern/workouts", "nk": "NT"}`
  - Error handling: Catch exceptions per-workout, don't abort the full batch

  **Must NOT do**:
  - Don't implement retry logic with exponential backoff (overkill)
  - Don't implement async/concurrent uploads (sequential is fine, avoids rate limiting)
  - Don't store any credentials in files — env vars only, garth handles token caching

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: API integration with reverse-engineered endpoints, auth flow, error handling — needs careful implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 5, 6
  - **Blocked By**: Tasks 1, 3

  **References**:

  **Pattern References**:
  - python-garminconnect source: `garminconnect/__init__.py` — `upload_workout()` method at line ~2342, `login()` method, `garmin_workouts` property for URL base

  **API/Type References**:
  - Upload endpoint: `POST /workout-service/workout` (JSON body)
  - Schedule endpoint: `POST /workout-service/schedule/{workout_id}` (body: `{"date": "YYYY-MM-DD"}`)
  - Delete endpoint: `DELETE /workout-service/workout/{workout_id}`
  - List workouts: `GET /workout-service/workouts` or similar (check python-garminconnect for exact method)
  - Required headers: `{"Referer": "https://connect.garmin.com/modern/workouts", "nk": "NT"}`

  **External References**:
  - python-garminconnect: https://github.com/cyberjunky/python-garminconnect — full API wrapper
  - garth: https://github.com/matin/garth — auth, token save/resume, direct `garth.connectapi()` calls
  - mkuthan/garmin-workouts garminclient.py: https://github.com/mkuthan/garmin-workouts/blob/master/garminworkouts/garmin/garminclient.py — schedule_workout() implementation reference

  **WHY Each Reference Matters**:
  - python-garminconnect is the auth and upload foundation — must match its API
  - mkuthan's garminclient.py is the ONLY reference for the schedule endpoint — python-garminconnect doesn't implement scheduling
  - garth handles the tricky Garmin SSO flow — don't try to reimplement auth

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Client initializes and authenticates
    Tool: Bash
    Preconditions: GARMIN_EMAIL and GARMIN_PASSWORD set in environment (or .env file)
    Steps:
      1. Run `uv run python -c "
         from workout_sync.garmin_client import GarminClient
         import os
         client = GarminClient(os.environ['GARMIN_EMAIL'], os.environ['GARMIN_PASSWORD'])
         client.login()
         print('Login successful')
         "`
      2. Verify "Login successful" is printed
      3. Verify ~/.garth directory was created with token files
    Expected Result: Authentication succeeds, tokens cached
    Failure Indicators: Auth error, missing garth tokens
    Evidence: .sisyphus/evidence/task-4-auth.txt

  Scenario: Upload a single test workout and schedule it
    Tool: Bash
    Preconditions: Authenticated client, valid workout JSON from builder
    Steps:
      1. Build a test workout JSON (e.g., "ról" for tomorrow's date)
      2. Upload and schedule it
      3. Verify workout_id is returned
      4. Query Garmin calendar for that date and verify workout appears
    Expected Result: Workout created and scheduled on correct date
    Failure Indicators: Upload error, schedule error, workout not on calendar
    Evidence: .sisyphus/evidence/task-4-upload-single.txt

  Scenario: Delete workouts by prefix
    Tool: Bash
    Preconditions: At least one [WS]-prefixed workout exists from previous scenario
    Steps:
      1. Call delete_workouts_by_prefix("[WS]")
      2. Verify deletion count > 0
      3. Re-run delete — verify count is 0 (all cleaned)
    Expected Result: All [WS]-prefixed workouts deleted
    Failure Indicators: Workouts still exist after delete, error during deletion
    Evidence: .sisyphus/evidence/task-4-delete.txt
  ```

  **Commit**: YES
  - Message: `feat: add Garmin Connect client with upload, schedule, and delete`
  - Files: `workout_sync/garmin_client.py`
  - Pre-commit: `uv run python -c "from workout_sync.garmin_client import GarminClient; print('OK')"`

- [x] 5. CLI Entry Point (argparse + glue + dry-run)

  **What to do**:
  - Implement `workout_sync/cli.py` with `main()` function
  - Implement `workout_sync/__main__.py` as entry: `from .cli import main; main()`
  - CLI interface:
    ```
    usage: workout-sync [-h] [--dry-run] xls_file

    Upload workout plan from XLS to Garmin Connect

    positional arguments:
      xls_file    Path to the XLS workout plan file

    optional arguments:
      -h, --help  show this help message and exit
      --dry-run   Parse and display workouts without uploading
    ```
  - `--dry-run` flow:
    1. Parse XLS → list of Workouts
    2. For each workout, build JSON and print summary:
       ```
       2026-03-09 (mán) samæfing: samæfing í Kaplakrika kl 18:00 [9.0 km]
         → Warmup: 2.0 km
         → Active: 5.0 km
         → Cooldown: 2.0 km
       2026-03-10 (þri) ról: ról [10.0 km]
         → Warmup: 1.0 km
         → Easy run: 8.0 km @ ~5:15/km
         → Cooldown: 1.0 km
       ...
       Total: 24 workouts, 198.0 km
       ```
  - Normal flow:
    1. Load credentials from env vars (GARMIN_EMAIL, GARMIN_PASSWORD)
    2. Parse XLS
    3. Print summary of what will be uploaded
    4. Login to Garmin Connect
    5. Delete existing [WS] workouts
    6. For each workout: build JSON → upload → schedule
    7. Print final summary: "Uploaded N workouts. M failed."
  - Load .env file with `python-dotenv` if present
  - Validate XLS file exists before proceeding

  **Must NOT do**:
  - No interactive prompts except for Garmin MFA if needed
  - No progress bars or fancy terminal UI
  - No config files beyond .env

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Glue code connecting already-built modules, straightforward argparse setup
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after all Wave 1 tasks)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 2, 3, 4

  **References**:

  **Pattern References**:
  - `workout_sync/parser.py` — `parse_xls(filepath)` function signature and `Workout` dataclass
  - `workout_sync/builder.py` — `build_workout_json(workout)` function signature
  - `workout_sync/garmin_client.py` — `GarminClient` class API

  **WHY Each Reference Matters**:
  - CLI glues these modules together — must use their exact interfaces

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Dry run displays all workouts correctly
    Tool: Bash
    Preconditions: Tasks 1-3 complete
    Steps:
      1. Run `uv run python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls`
      2. Verify output contains dates from 2026-03-09 through 2026-04-12
      3. Verify each workout shows structured steps (Warmup/Active/Cooldown)
      4. Verify ról workouts show pace target ~5:15/km
      5. Verify total count and km at the bottom
      6. Verify NO actual Garmin API calls were made (no login prompt)
    Expected Result: Clean formatted output of all workouts with structured step breakdown
    Failure Indicators: Import errors, missing workouts, no step breakdown, Garmin login attempted
    Evidence: .sisyphus/evidence/task-5-dry-run.txt

  Scenario: Missing XLS file shows helpful error
    Tool: Bash
    Preconditions: Tasks 1-3 complete
    Steps:
      1. Run `uv run python -m workout_sync --dry-run /nonexistent/file.xls`
      2. Verify error message mentions file not found
      3. Verify exit code is non-zero
    Expected Result: Clear error message, non-zero exit code
    Failure Indicators: Stack trace instead of clean error, exit code 0
    Evidence: .sisyphus/evidence/task-5-missing-file.txt

  Scenario: Missing credentials shows helpful error
    Tool: Bash
    Preconditions: Tasks 1-4 complete, NO GARMIN_EMAIL/PASSWORD set
    Steps:
      1. Run `env -u GARMIN_EMAIL -u GARMIN_PASSWORD uv run python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls`
      2. Verify error message mentions missing credentials
    Expected Result: Clear error about missing GARMIN_EMAIL/GARMIN_PASSWORD
    Failure Indicators: Cryptic error or crash
    Evidence: .sisyphus/evidence/task-5-no-creds.txt
  ```

  **Commit**: YES
  - Message: `feat: add CLI with dry-run mode and Garmin upload flow`
  - Files: `workout_sync/cli.py, workout_sync/__main__.py`
  - Pre-commit: `uv run python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls`

- [ ] 6. End-to-End QA

  **What to do**:
  - Run the full tool end-to-end with the real XLS file
  - Verify dry-run output matches expected workout schedule
  - If Garmin credentials are available, run actual upload and verify on Garmin Connect
  - Test wipe-and-reupload: run twice, verify no duplicates
  - Fix any issues found during QA

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: End-to-end verification requires running the full tool, checking output, and potentially debugging integration issues
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after all implementation)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - All `workout_sync/*.py` files — the complete implementation
  - `~/Downloads/Sindri Guðmunds - mars.xls` — the actual input file

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full dry-run with real XLS
    Tool: Bash
    Preconditions: All tasks 1-5 complete
    Steps:
      1. Run `uv run python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls`
      2. Capture full output
      3. Verify 22-25 workouts listed (non-rest days across 5 weeks)
      4. Verify first workout is 2026-03-09 samæfing 9.0km
      5. Verify last workout is 2026-04-11 ról 20.0km
      6. Verify hraðaæf on 2026-03-23 shows interval steps
      7. Verify jafnt on 2026-04-02 shows ~4:50/km pace
      8. Verify no rest days (hv) in output
    Expected Result: Complete, correct workout schedule
    Evidence: .sisyphus/evidence/task-6-full-dry-run.txt

  Scenario: Full upload to Garmin Connect (if credentials available)
    Tool: Bash
    Preconditions: GARMIN_EMAIL and GARMIN_PASSWORD set
    Steps:
      1. Run `uv run python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls`
      2. Verify authentication succeeds
      3. Verify deletion step reports count of removed [WS] workouts (0 on first run)
      4. Verify upload reports "Uploaded N workouts. 0 failed."
      5. Run again — verify deletion count matches N, then re-uploads
    Expected Result: Workouts uploaded and scheduled, re-run is idempotent
    Failure Indicators: Auth failure, upload errors, schedule errors, duplicates after re-run
    Evidence: .sisyphus/evidence/task-6-full-upload.txt

  Scenario: Verify workouts on Garmin calendar
    Tool: Bash
    Preconditions: Upload completed successfully
    Steps:
      1. Use python-garminconnect to query scheduled workouts for March-April 2026
      2. Verify workout names start with "[WS]"
      3. Verify dates match the XLS plan
      4. Verify workout count matches dry-run count
    Expected Result: All workouts present on Garmin calendar with correct dates
    Failure Indicators: Missing workouts, wrong dates, wrong names
    Evidence: .sisyphus/evidence/task-6-verify-calendar.txt
  ```

  **Commit**: YES (if fixes needed)
  - Message: `fix: address e2e QA findings`
  - Files: Any files that needed fixes

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run linter + type check if configured. Review all changed files for: `as Any` abuse, empty catches, print-debugging left in, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic variable names. Verify the code is clean and minimal.
  Output: `Lint [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run `python -m workout_sync --dry-run` on the actual XLS file. Verify output matches expected workout schedule. If Garmin credentials available, run actual upload and check Garmin Connect calendar.
  Output: `Scenarios [N/N pass] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual code. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Flag any web frameworks, databases, or over-engineering.
  Output: `Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

- **Wave 1 commit**: `feat: add project scaffold, XLS parser, and workout builder`
  - pyproject.toml, workout_sync/__init__.py, parser.py, builder.py, .env.example
- **Wave 2 commit**: `feat: add Garmin client and CLI entry point`
  - garmin_client.py, cli.py, __main__.py
- **Final commit** (if any fixes from QA): `fix: address QA findings`

---

## Success Criteria

### Verification Commands
```bash
# Dry run — should print all non-rest workouts with dates and structured steps
python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls

# Actual upload — should authenticate and upload to Garmin Connect
python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls

# Re-run — should wipe previous uploads and re-upload cleanly
python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] Dry run outputs correct workout schedule
- [ ] Workouts appear on Garmin Connect calendar with correct dates and structured steps
