# XLS Format

The input file is an Icelandic coach's training plan exported from Excel.

## Structure

| Row Range | Content |
|-----------|---------|
| 0-7       | Headers (athlete name, month, column labels) |
| 8-52      | Data rows (daily workout entries + weekly summaries + separators) |
| 53-60     | Legend (workout type explanations) |

6 columns:

| Column | Content | Cell Type |
|--------|---------|-----------|
| 0      | Date    | Date (ctype 3) for workout rows, text/empty for summaries |
| 1      | Day name (Icelandic: mán, þri, mið, fim, fös, lau, sun) | Text |
| 2      | Description (workout type + location/notes) | Text |
| 3      | Distance in km | Number (ctype 2), empty for rest/strength |
| 4      | (unused) | — |
| 5      | Notes | Text |

## Row Filtering

Only rows where column 0 is a date cell (`ctype == 3`) are processed. This naturally skips:
- Weekly summary rows ("vikan X - Y" pattern in col 2)
- Empty separator rows between weeks
- Header and legend rows

## Icelandic Workout Types

| Type | Icelandic | Meaning | Has Pace Target |
|------|-----------|---------|-----------------|
| ról | ról | Easy run | Yes (5:04-6:05/km) |
| samæfing | samæfing | Group training | No |
| hraðaæf | hraðaæfing | Speed workout | No (INTERVAL intensity) |
| jafnt | jafnt | Steady/tempo run | Yes (4:30-5:10/km) |
| styrktaræfing | styrktaræfing | Strength training | N/A (not running) |
| fartleikur | fartleikur | Fartlek | No |

## Classification Order (Critical)

The keyword check order in `_classify_workout_type()` matters:

1. **ról** — checked first
2. **hraðaæf** — before samæfing
3. **jafnt** — MUST come before samæfing because descriptions like `"jafnt (ekki samæfing v/Skírdagur)"` contain both keywords. The parenthetical means "not samæfing" (negative context).
4. **samæfing** — also catches truncated `"samæf"` substrings
5. **styrktaræfing** — strength training
6. **fartleikur** — also matches `"fartleik"` (truncated)
7. **Hlaupasería** (case-sensitive) — falls back to samæfing
8. **other** — fallback

## Rest Day Filtering

A row is a rest day if: `distance_km == 0.0 AND workout_type != "styrktaræfing"`

This keeps 0km strength sessions (real workouts) while filtering pure rest entries like `"hv"` (hvíld = rest).

## Example Data

```
2026-03-10 (þri) ról: ról [10.0 km]
2026-03-11 (mið) styrktaræfing: hv eða styrktaræfing [0.0 km]
2026-04-02 (fim) jafnt: jafnt (ekki samæfing v/Skírdagur) [10.0 km]
```

This month's plan: 24 workouts across March 9 – April 11, 2026 (ról=13, samæfing=6, styrktaræfing=2, hraðaæf=2, jafnt=1).
