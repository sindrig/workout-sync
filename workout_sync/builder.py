"""Builder module: converts parsed Workout objects into Garmin Connect workout JSON."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Workout:
    """Workout data parsed from the training plan spreadsheet.

    This is a local definition for type hints. The canonical Workout
    dataclass will be provided by the parser module (Task 2).
    """

    date: str
    workout_type: str  # ról, samæfing, hraðaæf, jafnt, styrktaræfing, fartleikur
    distance_km: float
    description: str


# ---------------------------------------------------------------------------
# Sport type constants
# ---------------------------------------------------------------------------
RUNNING_SPORT = {"sportTypeId": 1, "sportTypeKey": "running"}
STRENGTH_SPORT = {"sportTypeId": 5, "sportTypeKey": "strength_training"}

# ---------------------------------------------------------------------------
# Garmin ExecutableStepDTO constants
# ---------------------------------------------------------------------------
STEP_TYPES = {
    "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup"},
    "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
    "interval": {"stepTypeId": 3, "stepTypeKey": "interval"},
    "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery"},
}

END_CONDITIONS = {
    "lap.button": {"conditionTypeId": 1, "conditionTypeKey": "lap.button"},
    "distance": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
}

TARGET_TYPES = {
    "no.target": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
    "pace.zone": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
}

# Pace targets: (fast_pace, slow_pace) as "M:SS" per km
# Counterintuitive: fast = fewer sec/km = higher m/s, slow = more sec/km = lower m/s
PACE_TARGETS: dict[str, tuple[str, str]] = {
    "ról": ("5:04", "6:05"),
    "jafnt": ("4:30", "5:10"),
}

# warmup_km, cooldown_km (active_km = total - warmup - cooldown)
STEP_TEMPLATES: dict[str, dict] = {
    "ról": {"warmup_km": 1.0, "cooldown_km": 1.0},
    "samæfing": {"warmup_km": 2.0, "cooldown_km": 2.0},
    "hraðaæf": {"warmup_km": 2.5, "cooldown_km": 2.0},
    "jafnt": {"warmup_km": 1.0, "cooldown_km": 1.0},
    "fartleikur": {"warmup_km": 2.0, "cooldown_km": 2.0},
}


def pace_range_to_ms(fast_pace: str, slow_pace: str) -> tuple[float, float]:
    """Convert pace range to (slow_ms, fast_ms) in m/s.

    Garmin convention: targetValueOne = slow end, targetValueTwo = fast end.
    """

    def _to_sec(pace: str) -> int:
        parts = pace.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    slow_sec = _to_sec(slow_pace)
    fast_sec = _to_sec(fast_pace)

    slow_ms = 1000.0 / slow_sec
    fast_ms = 1000.0 / fast_sec

    return (round(slow_ms, 4), round(fast_ms, 4))


def _make_step(
    step_type_key: str,
    step_order: int,
    end_condition_key: str = "distance",
    end_condition_value: float | None = None,
    pace_target: tuple[str, str] | None = None,
) -> dict:
    """Build a single Garmin ExecutableStepDTO."""
    step: dict = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {**STEP_TYPES[step_type_key]},
        "endCondition": {**END_CONDITIONS[end_condition_key]},
        "endConditionValue": end_condition_value,
        "targetType": {**TARGET_TYPES["no.target"]},
    }

    if pace_target:
        slow_ms, fast_ms = pace_range_to_ms(pace_target[0], pace_target[1])
        step["targetType"] = {**TARGET_TYPES["pace.zone"]}
        step["targetValueOne"] = slow_ms
        step["targetValueTwo"] = fast_ms

    return step


def warmup_step(distance_km: float, step_order: int = 1) -> dict:
    return _make_step("warmup", step_order, "distance", distance_km * 1000)


def active_step(
    distance_km: float,
    step_order: int = 2,
    pace_target: tuple[str, str] | None = None,
    step_type_key: str = "interval",
) -> dict:
    return _make_step(
        step_type_key, step_order, "distance", distance_km * 1000, pace_target
    )


def cooldown_step(distance_km: float, step_order: int = 3) -> dict:
    return _make_step("cooldown", step_order, "distance", distance_km * 1000)


def _strength_step(step_order: int = 1) -> dict:
    return _make_step("interval", step_order, "lap.button")


# ---------------------------------------------------------------------------
# Step builders per workout type
# ---------------------------------------------------------------------------
def _build_running_steps(
    workout: Workout,
    warmup_km: float,
    cooldown_km: float,
    pace_target: tuple[str, str] | None = None,
) -> list[dict]:
    total_m = workout.distance_km * 1000

    min_padding = warmup_km + cooldown_km
    if workout.distance_km <= min_padding:
        ratio = workout.distance_km / min_padding if min_padding > 0 else 0
        warmup_km = round(warmup_km * ratio, 2)
        cooldown_km = round(cooldown_km * ratio, 2)

    warmup_m = warmup_km * 1000
    cooldown_m = cooldown_km * 1000
    active_m = max(total_m - warmup_m - cooldown_m, 0)

    steps: list[dict] = []
    order = 1

    if warmup_m > 0:
        steps.append(warmup_step(warmup_km, step_order=order))
        order += 1

    if active_m > 0:
        steps.append(
            active_step(active_m / 1000, step_order=order, pace_target=pace_target)
        )
        order += 1

    if cooldown_m > 0:
        steps.append(cooldown_step(cooldown_km, step_order=order))

    return steps


def _build_steps(workout: Workout) -> list[dict]:
    wtype = workout.workout_type.lower().strip()

    if wtype == "styrktaræfing":
        return [_strength_step()]

    if wtype in STEP_TEMPLATES:
        tmpl = STEP_TEMPLATES[wtype]
        pace = PACE_TARGETS.get(wtype)
        return _build_running_steps(
            workout,
            warmup_km=tmpl["warmup_km"],
            cooldown_km=tmpl["cooldown_km"],
            pace_target=pace,
        )

    if workout.distance_km > 0:
        return [active_step(workout.distance_km, step_order=1)]
    return [_strength_step()]


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_workout_json(workout: Workout) -> dict:
    wtype = workout.workout_type.lower().strip()
    sport = {**STRENGTH_SPORT} if wtype == "styrktaræfing" else {**RUNNING_SPORT}
    steps = _build_steps(workout)

    return {
        "workoutName": f"[WS] {workout.description}",
        "sportType": sport,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": sport,
                "workoutSteps": steps,
            }
        ],
    }
