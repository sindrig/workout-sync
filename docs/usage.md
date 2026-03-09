# Usage

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Garmin Connect account (for upload mode)

## Install Dependencies

```bash
uv sync
```

## Dry Run (Preview)

Parse the XLS and print a structured summary without touching Garmin:

```bash
uv run python -m workout_sync --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

Example output:

```
=== DRY RUN ===

2026-03-10 (þri) ról: ról [10.0 km]
  → Warmup: 1.0 km
  → Active: 8.0 km @ ~5:04-6:05/km
  → Cooldown: 1.0 km
2026-04-02 (fim) jafnt: jafnt  (ekki samæfing v/Skírdagur) [10.0 km]
  → Warmup: 1.0 km
  → Active: 8.0 km @ ~4:30-5:10/km
  → Cooldown: 1.0 km
...

Total: 24 workouts, 254.0 km
```

## Upload to Garmin Connect

Set credentials:

```bash
cp .env.example .env
# Edit .env with your Garmin email and password
```

Run without `--dry-run`:

```bash
uv run python -m workout_sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

This will:
1. Parse the XLS
2. Log in to Garmin Connect (prompts for MFA if enabled)
3. Delete all existing `[WS]`-prefixed workouts (idempotent wipe)
4. Upload each workout and schedule it on the calendar date

## MFA

If your Garmin account has MFA enabled, you'll be prompted on stdin:

```
Enter MFA code: 123456
```

## Token Caching

After first login, OAuth tokens are cached in `~/.garth/`. Subsequent runs reuse cached tokens (no password prompt unless tokens expire).
