# Usage

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Garmin Connect account

## Install Dependencies

```bash
uv sync
```

## Upload (push plan to Garmin)

### Dry Run (Preview)

Parse the XLS and print a structured summary without touching Garmin:

```bash
uv run workout-sync upload --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
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

### Live Upload

Set credentials:

```bash
cp .env.example .env
# Edit .env with your Garmin email and password
```

Run:

```bash
uv run workout-sync upload ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

This will:
1. Parse the XLS
2. Log in to Garmin Connect (prompts for MFA if enabled)
3. Delete all existing `[WS]`-prefixed workouts (idempotent wipe)
4. Upload each workout and schedule it on the calendar date

### Backward Compatibility

Running without a subcommand defaults to `upload`:

```bash
uv run workout-sync ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

## Download (pull actual distances from Garmin)

Fetch completed running activities from Garmin Connect and write the actual distances into the "km í raun" column (column 4) of the XLS file.

### Dry Run

```bash
uv run workout-sync download --dry-run ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

Example output:

```
=== DRY RUN — KM Í RAUN (increment: 0.5 km) ===

  2026-03-10 (þri) ról                                       plan:  10.0 km  actual:  10.0 km (Δ +0.0)
  2026-03-11 (mið) samæfing                                   plan:  12.0 km  actual:  11.5 km (Δ -0.5)
...

14 day(s) with activity data, 10 without.

Dry run — no files modified.
```

### Live Download

```bash
uv run workout-sync download ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

This will:
1. Parse the XLS to find all workout date rows
2. Log in to Garmin Connect
3. Fetch running activities for the date range
4. Sum multiple activities on the same date
5. Round distances to the nearest increment (default 0.5 km)
6. Write values into column 4 and save as `.xlsx`

### Custom Increment

Change the rounding increment (default: 0.5 km):

```bash
uv run workout-sync download --increment 1.0 ~/Downloads/Sindri\ Guðmunds\ -\ mars.xls
```

### Output Format

The download command edits the `.xls` file in-place, preserving all existing formatting and formulas. A copy of the original workbook is made via `xlutils`, the "km í raun" column is updated, and the file is saved back to the same path.

## MFA

If your Garmin account has MFA enabled, you'll be prompted on stdin:

```
Enter MFA code: 123456
```

## Token Caching

After first login, OAuth tokens are cached in `~/.garth/`. Subsequent runs reuse cached tokens (no password prompt unless tokens expire).
