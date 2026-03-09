# Architecture

## Overview

workout-sync is a single-purpose Python CLI that parses an Icelandic coach's XLS training plan and uploads structured workouts to Garmin Connect's training calendar. Personal use, no UI.

## Data Flow

```
XLS file → parser.py → [Workout] → builder.py → [JSON] → garmin_client.py → Garmin Connect API
                                                       ↘ cli.py (dry-run print)
```

1. **parser.py** reads the XLS with `xlrd`, extracts rows 8+ as `Workout` dataclasses
2. **builder.py** converts each `Workout` into Garmin Connect workout JSON (warmup/active/cooldown steps with pace targets)
3. **garmin_client.py** authenticates via `python-garminconnect` + `garth`, uploads workout JSON, schedules it on the calendar
4. **cli.py** orchestrates the flow: parse → (dry-run preview | delete existing + upload)

## File Structure

```
workout_sync/
├── __init__.py         # Package version (0.1.0)
├── __main__.py         # `python -m workout_sync` entry point
├── cli.py              # CLI arg parsing, dry-run display, upload orchestration
├── parser.py           # XLS parsing, workout type classification, rest day filtering
├── builder.py          # Workout → Garmin JSON conversion, pace targets, step templates
└── garmin_client.py    # Garmin Connect auth, upload, schedule, delete
```

## Module Responsibilities

### parser.py
- Opens XLS with `xlrd`, iterates rows 8+ (rows 0-7 are headers, 53-60 are legend)
- Filters by date cell type (ctype == 3) to skip summary/separator rows
- Classifies Icelandic workout descriptions into types (ról, samæfing, etc.)
- Filters rest days (0 km, non-strength)
- Returns `list[Workout]` sorted by date

### builder.py
- Maps workout types to step templates (warmup/cooldown distances) and pace targets
- Builds Garmin-compatible JSON with WorkoutStep dicts
- Handles edge cases: short distances scale warmup/cooldown proportionally
- Pace conversion: "M:SS"/km strings → m/s floats for Garmin API

### garmin_client.py
- Wraps `python-garminconnect` (`Garmin` class) for auth with token caching (`~/.garth`)
- Idempotent uploads: deletes all `[WS]`-prefixed workouts, then uploads fresh
- Uses `garth` directly for schedule/delete endpoints (not exposed by the library)
- MFA support via interactive prompt

### cli.py
- `--dry-run`: parse + build + pretty-print (no Garmin calls)
- Normal mode: parse + build + login + delete old + upload + schedule
- Credentials from env vars (`GARMIN_EMAIL`, `GARMIN_PASSWORD`)

## Design Constraints

- No web server, no database, no GUI
- No generic/configurable parser — hardcoded to this exact XLS format
- No pandas — xlrd only
- No test framework
- No over-engineered abstractions
- Minimal dependencies: garminconnect, xlrd, python-dotenv
