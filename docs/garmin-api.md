# Garmin Connect API

## Authentication

Uses `python-garminconnect` (`Garmin` class) which wraps `garth` for OAuth.

- Credentials: `GARMIN_EMAIL` + `GARMIN_PASSWORD` env vars
- Token caching: garth saves OAuth1 + OAuth2 tokens to `~/.garth/` as JSON
- Login flow: try loading cached tokens → catch any exception → fall back to fresh login
- MFA: `prompt_mfa` callback prompts on stdin when Garmin requires it

## Endpoints

### Upload Workout
- Handled by `Garmin.upload_workout(json_dict)` from python-garminconnect
- `POST /workout-service/workout` — returns `{"workoutId": int, ...}`

### Schedule Workout
- NOT exposed by python-garminconnect — use garth directly
- `POST /workout-service/schedule/{workout_id}` with body `{"date": "YYYY-MM-DD"}`
- **Requires explicit headers** (see gotcha below)

### Delete Workout
- NOT exposed by python-garminconnect — use garth directly
- `DELETE /workout-service/workout/{workout_id}`

### List Workouts
- `Garmin.get_workouts(start=0, limit=100)` — typed as `dict` but returns `list[dict]`
- Paginate by incrementing `start` until batch is empty or < limit

## Garth Usage

```python
# Schedule (POST)
client.garth.post(
    "connectapi",
    f"/workout-service/schedule/{workout_id}",
    json={"date": date_str},
    api=True,
    headers={
        "Referer": "https://connect.garmin.com/modern/workouts",
        "nk": "NT",
    },
)

# Delete (DELETE)
client.garth.request(
    "DELETE",
    "connectapi",
    f"/workout-service/workout/{workout_id}",
    api=True,
)
```

## Critical Gotcha: `api=True` Does NOT Add Required Headers

The `api=True` flag on garth only:
1. Asserts OAuth1 token exists
2. Refreshes OAuth2 token if expired
3. Adds the `Authorization` header

It does **NOT** add `Referer` or `nk: NT` headers. These must be passed explicitly for the schedule endpoint (and potentially other workout-service endpoints). Without them, requests may fail silently or return 403.

Reference: [mkuthan/garmin-workouts](https://github.com/mkuthan/garmin-workouts) explicitly passes these headers to all workout-service calls.

## Workout JSON Schema

The builder outputs Garmin's `ExecutableStepDTO` format that `python-garminconnect.upload_workout()` posts directly:

```json
{
  "workoutName": "[WS] ról",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 1000.0,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 8000.0,
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
        "targetValueOne": 2.7397,
        "targetValueTwo": 3.2895
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 1000.0,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}
      }
    ]
  }]
}
```

### Step Types (stepType)
- `{"stepTypeId": 1, "stepTypeKey": "warmup"}` — warmup
- `{"stepTypeId": 2, "stepTypeKey": "cooldown"}` — cooldown
- `{"stepTypeId": 3, "stepTypeKey": "interval"}` — main effort / active step
- `{"stepTypeId": 4, "stepTypeKey": "recovery"}` — recovery between intervals

### End Conditions (endCondition)
- `{"conditionTypeId": 1, "conditionTypeKey": "lap.button"}` — open-ended (strength training)
- `{"conditionTypeId": 3, "conditionTypeKey": "distance"}` — value in meters (endConditionValue)

### Target Types (targetType)
- `{"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}` — no pace constraint
- `{"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"}` — pace zone, values in m/s (targetValueOne=slow end, targetValueTwo=fast end)

### Sport Types
- Running: `{"sportTypeId": 1, "sportTypeKey": "running"}`
- Strength: `{"sportTypeId": 4, "sportTypeKey": "strength_training"}`

## Idempotency Strategy

Wipe-and-reupload: delete all workouts prefixed with `[WS]`, then upload fresh. This avoids duplicate detection complexity. All workout names are prefixed with `[WS]` to identify managed workouts.
