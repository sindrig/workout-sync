# AGENTS.md — workout-sync

Python CLI that parses an Icelandic coach's XLS workout training plan and uploads structured workouts to Garmin Connect's training calendar.

## Documentation

Refer to `docs/` for detailed context on each area:

| Document | What it covers |
|----------|---------------|
| [docs/architecture.md](docs/architecture.md) | Module overview, data flow, file structure, design constraints |
| [docs/xls-format.md](docs/xls-format.md) | XLS row/column layout, Icelandic workout types, classification order, rest day filtering |
| [docs/garmin-api.md](docs/garmin-api.md) | Workout JSON schema, Garmin endpoints, auth/token caching, garth `api=True` header gotcha |
| [docs/configuration.md](docs/configuration.md) | Pace targets, step templates, how to change them, env vars |
| [docs/usage.md](docs/usage.md) | CLI invocation, dry-run, upload flow, MFA, token caching |

## Quick Reference

### Tech Stack
- Python 3.13+, managed by [uv](https://docs.astral.sh/uv/)
- `xlrd` for XLS parsing (no pandas)
- `python-garminconnect` + `garth` for Garmin Connect API
- `python-dotenv` for env var loading

### Project Layout
```
workout_sync/
  __init__.py         # version
  __main__.py         # entry point
  cli.py              # CLI orchestration, dry-run display
  parser.py           # XLS → Workout dataclasses
  builder.py          # Workout → Garmin JSON (pace targets, step templates)
  garmin_client.py    # Garmin auth, upload, schedule, delete
docs/                 # detailed documentation (see table above)
.env.example          # credential template
```

### Key Gotchas
- **Classification order** in `parser.py`: "jafnt" must be checked before "samæfing" — see [docs/xls-format.md](docs/xls-format.md)
- **garth `api=True`** does NOT add `Referer`/`nk` headers — see [docs/garmin-api.md](docs/garmin-api.md)
- **Pace math is counterintuitive**: faster pace = fewer sec/km = higher m/s value — see [docs/configuration.md](docs/configuration.md)
- **`get_workouts()` return type** is typed as `dict` but returns `list[dict]` — see [docs/garmin-api.md](docs/garmin-api.md)
