# Configuration

All workout configuration is hardcoded in `workout_sync/builder.py`. There are no config files — edit the source directly.

## Pace Targets

```python
# builder.py, lines 32-35
PACE_TARGETS: dict[str, tuple[str, str]] = {
    "ról": ("5:04", "6:05"),      # easy run: 5:04-6:05 per km
    "jafnt": ("4:30", "5:10"),    # steady run: 4:30-5:10 per km
}
```

Each entry: `"workout_type": ("fast_pace", "slow_pace")` in M:SS per km.

- **fast_pace** = fastest acceptable pace (lower bound on watch) = fewer sec/km = higher m/s
- **slow_pace** = slowest acceptable pace (upper bound on watch) = more sec/km = lower m/s

### To change a pace range

Edit the tuple. Example — make ról easier:
```python
"ról": ("5:00", "6:30"),
```

### To add pace targets to a new workout type

Add an entry with the key matching the workout type string:
```python
"samæfing": ("4:15", "4:45"),
```

Workout types NOT in `PACE_TARGETS` get no pace constraint on their active step (just a distance goal).

### Pace conversion (how it works internally)

`pace_range_to_ms(fast_pace, slow_pace)` converts M:SS strings → meters per second:
1. Parse "M:SS" → total seconds per km
2. Convert sec/km → m/s: `1000.0 / seconds_per_km`
3. Return `(low_ms, high_ms)` — Garmin wants `targetValueOne=slow`, `targetValueTwo=fast`

The conversion is counterintuitive: faster pace = fewer sec/km = **higher** m/s value.

## Step Templates

```python
# builder.py, lines 41-47
STEP_TEMPLATES: dict[str, dict] = {
    "ról":       {"warmup_km": 1.0, "cooldown_km": 1.0},
    "samæfing":  {"warmup_km": 2.0, "cooldown_km": 2.0},
    "hraðaæf":   {"warmup_km": 2.5, "cooldown_km": 2.0},
    "jafnt":     {"warmup_km": 1.0, "cooldown_km": 1.0},
    "fartleikur":{"warmup_km": 2.0, "cooldown_km": 2.0},
}
```

Active distance = total distance − warmup − cooldown.

If total distance is too small for warmup + cooldown, both are scaled down proportionally (no negative distances).

### To adjust warmup/cooldown distances

Edit the dict values directly. Example — longer warmup for speed work:
```python
"hraðaæf": {"warmup_km": 3.0, "cooldown_km": 2.0},
```

## Workout Name Prefix

All uploaded workouts are named `[WS] {description}`. The `[WS]` prefix is used for idempotent uploads — before uploading, all existing `[WS]` workouts are deleted. Defined in `build_workout_json()`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GARMIN_EMAIL` | Yes (upload mode) | Garmin Connect email |
| `GARMIN_PASSWORD` | Yes (upload mode) | Garmin Connect password |

Set via `.env` file (loaded by python-dotenv) or shell environment. See `.env.example`.
