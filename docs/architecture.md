# Architecture

## Overview

workout-sync is a Python CLI that syncs workout data between an Icelandic coach's XLS training plan and Garmin Connect. It supports two directions:

- **Upload**: Parse XLS → build Garmin workout JSON → upload to Garmin calendar
- **Download**: Fetch completed activities from Garmin → write actual distances back into the XLS

## Data Flow

```
Upload:
  XLS file → parser.py → [Workout] → builder.py → [JSON] → garmin_client.py → Garmin Connect API
                                                        ↘ cli.py (dry-run print)

Download:
  XLS file → parser.py → [WorkoutRow] (dates + row indices)
  Garmin Connect API → garmin_client.py → [activities] → downloader.py → XLS column 4 (km í raun)
```

1. **parser.py** reads the XLS with `xlrd`, extracts rows 8+ as `Workout` dataclasses (upload) or `WorkoutRow` structs (download)
2. **builder.py** converts each `Workout` into Garmin Connect workout JSON (warmup/active/cooldown steps with pace targets)
3. **garmin_client.py** authenticates via `python-garminconnect` + `garth`, uploads workouts or fetches activities
4. **downloader.py** matches Garmin activities to XLS date rows, rounds distances, writes via `openpyxl`
5. **cli.py** orchestrates both flows via `upload` and `download` subcommands

## File Structure

```
workout_sync/
├── __init__.py         # Package version (0.1.0)
├── __main__.py         # `python -m workout_sync` entry point
├── cli.py              # CLI subcommands (upload/download), arg parsing, orchestration
├── parser.py           # XLS parsing, workout type classification, rest day filtering
├── builder.py          # Workout → Garmin JSON conversion, pace targets, step templates
├── garmin_client.py    # Garmin Connect auth, upload, schedule, delete, activity fetch
└── downloader.py       # Garmin activities → XLS write-back (km í raun)
```

## Module Responsibilities

### parser.py
- Opens XLS with `xlrd`, iterates rows 8+ (rows 0-7 are headers, 53-60 are legend)
- Filters by date cell type (ctype == 3) to skip summary/separator rows
- Classifies Icelandic workout descriptions into types (ról, samæfing, etc.)
- `parse_xls()`: returns filtered `list[Workout]` (rest days excluded) for upload
- `parse_xls_rows()`: returns unfiltered `list[WorkoutRow]` with row indices for download write-back

### builder.py
- Maps workout types to step templates (warmup/cooldown distances) and pace targets
- Builds Garmin-compatible JSON with WorkoutStep dicts
- Handles edge cases: short distances scale warmup/cooldown proportionally
- Pace conversion: "M:SS"/km strings → m/s floats for Garmin API

### garmin_client.py
- Wraps `python-garminconnect` (`Garmin` class) for auth with token caching (`~/.garth`)
- Idempotent uploads: deletes all `[WS]`-prefixed workouts, then uploads fresh
- Uses `garth` directly for schedule/delete endpoints (not exposed by the library)
- `get_activities_by_date()`: fetches completed running activities for a date range
- MFA support via interactive prompt

### downloader.py
- `fetch_actual_distances()`: calls Garmin API, sums multiple activities per date
- `round_to_increment()`: rounds distances to configurable increment (default 0.5 km)
- `write_actual_km()`: writes rounded values to column 4 via `openpyxl`, saves as `.xlsx`

### cli.py
- `upload` subcommand: parse + build + login + delete old + upload + schedule (or `--dry-run`)
- `download` subcommand: parse rows + login + fetch activities + round + write (or `--dry-run`)
- No subcommand defaults to `upload` for backward compatibility
- Credentials from env vars (`GARMIN_EMAIL`, `GARMIN_PASSWORD`)

## Design Constraints

- No web server, no database, no GUI
- No generic/configurable parser — hardcoded to this exact XLS format
- No pandas — xlrd for reading, openpyxl for writing
- No test framework
- No over-engineered abstractions
- Minimal dependencies: garminconnect, xlrd, openpyxl, python-dotenv
