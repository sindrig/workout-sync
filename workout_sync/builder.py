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
STRENGTH_SPORT = {"sportTypeId": 4, "sportTypeKey": "strength_training"}

# ---------------------------------------------------------------------------
# Pace targets (hardcoded per coach's legend)
# ---------------------------------------------------------------------------
PACE_TARGETS: dict[str, str] = {
    "ról": "5:15",
    "jafnt": "4:50",
}

# Pace tolerance: ±10 seconds around target
PACE_TOLERANCE_SEC = 10

# ---------------------------------------------------------------------------
# Workout type → step template config
# warmup_km, cooldown_km (active_km = total - warmup - cooldown)
# ---------------------------------------------------------------------------
STEP_TEMPLATES: dict[str, dict] = {
    "ról": {"warmup_km": 1.0, "cooldown_km": 1.0},
    "samæfing": {"warmup_km": 2.0, "cooldown_km": 2.0},
    "hraðaæf": {"warmup_km": 2.5, "cooldown_km": 2.0},
    "jafnt": {"warmup_km": 1.0, "cooldown_km": 1.0},
    "fartleikur": {"warmup_km": 2.0, "cooldown_km": 2.0},
}


# ---------------------------------------------------------------------------
# Pace conversion
# ---------------------------------------------------------------------------
def pace_str_to_ms(pace: str) -> tuple[float, float]:
    """Convert pace string "M:SS" per km to (low_ms, high_ms) in m/s.

    Returns a target range of ±PACE_TOLERANCE_SEC around the given pace.

    The *slower* pace (more seconds/km) yields a *lower* m/s value and the
    *faster* pace yields a *higher* m/s value.

    Garmin convention: targetValueOne = slow end, targetValueTwo = fast end.

    Example:
        >>> pace_str_to_ms("5:15")  # 5:15/km ± 10s → 5:05-5:25
        (3.08..., 3.28...)
    """
    parts = pace.split(":")
    total_sec = int(parts[0]) * 60 + int(parts[1])

    slow_sec = total_sec + PACE_TOLERANCE_SEC  # slower = more sec/km
    fast_sec = total_sec - PACE_TOLERANCE_SEC  # faster = fewer sec/km

    low_ms = 1000.0 / slow_sec  # slower pace → lower m/s
    high_ms = 1000.0 / fast_sec  # faster pace → higher m/s

    return (round(low_ms, 2), round(high_ms, 2))


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------
def warmup_step(distance_km: float, step_order: int = 1) -> dict:
    """Build a warmup step with the given distance (no pace target)."""
    return {
        "type": "WorkoutStep",
        "stepOrder": step_order,
        "intensity": "WARMUP",
        "durationType": "DISTANCE",
        "durationValue": distance_km * 1000,  # convert km → meters
        "targetType": "NO_TARGET",
        "targetValueOne": None,
        "targetValueTwo": None,
    }


def active_step(
    distance_km: float,
    step_order: int = 2,
    pace_target: str | None = None,
    intensity: str = "ACTIVE",
) -> dict:
    """Build an active/interval step with optional pace target.

    Args:
        distance_km: Distance in kilometers.
        step_order: 1-indexed position within the segment.
        pace_target: Optional pace string like "5:15" (min:sec per km).
        intensity: Step intensity — "ACTIVE" or "INTERVAL".
    """
    step: dict = {
        "type": "WorkoutStep",
        "stepOrder": step_order,
        "intensity": intensity,
        "durationType": "DISTANCE",
        "durationValue": distance_km * 1000,
        "targetType": "NO_TARGET",
        "targetValueOne": None,
        "targetValueTwo": None,
    }

    if pace_target:
        low_ms, high_ms = pace_str_to_ms(pace_target)
        step["targetType"] = "PACE"
        step["targetValueOne"] = low_ms
        step["targetValueTwo"] = high_ms

    return step


def cooldown_step(distance_km: float, step_order: int = 3) -> dict:
    """Build a cooldown step with the given distance (no pace target)."""
    return {
        "type": "WorkoutStep",
        "stepOrder": step_order,
        "intensity": "COOLDOWN",
        "durationType": "DISTANCE",
        "durationValue": distance_km * 1000,
        "targetType": "NO_TARGET",
        "targetValueOne": None,
        "targetValueTwo": None,
    }


def _strength_step(step_order: int = 1) -> dict:
    """Build a strength training step using LAP_BUTTON_PRESS duration."""
    return {
        "type": "WorkoutStep",
        "stepOrder": step_order,
        "intensity": "ACTIVE",
        "durationType": "LAP_BUTTON_PRESS",
        "durationValue": None,
        "targetType": "NO_TARGET",
        "targetValueOne": None,
        "targetValueTwo": None,
    }


# ---------------------------------------------------------------------------
# Step builders per workout type
# ---------------------------------------------------------------------------
def _build_running_steps(
    workout: Workout,
    warmup_km: float,
    cooldown_km: float,
    pace_target: str | None = None,
    active_intensity: str = "ACTIVE",
) -> list[dict]:
    """Build warmup → active → cooldown steps for a running workout.

    Ensures all distances are positive. If total distance is too small for
    warmup + cooldown, the warmup and cooldown are scaled down proportionally.
    """
    total_m = workout.distance_km * 1000

    # Guard: ensure no negative active distance
    min_padding = warmup_km + cooldown_km
    if workout.distance_km <= min_padding:
        # Scale warmup/cooldown proportionally to fit
        ratio = workout.distance_km / min_padding if min_padding > 0 else 0
        warmup_km = round(warmup_km * ratio, 2)
        cooldown_km = round(cooldown_km * ratio, 2)

    warmup_m = warmup_km * 1000
    cooldown_m = cooldown_km * 1000
    active_m = total_m - warmup_m - cooldown_m

    # Final safety: clamp to zero
    active_m = max(active_m, 0)

    steps: list[dict] = []
    order = 1

    if warmup_m > 0:
        steps.append(warmup_step(warmup_km, step_order=order))
        order += 1

    if active_m > 0:
        steps.append(
            active_step(
                active_m / 1000,
                step_order=order,
                pace_target=pace_target,
                intensity=active_intensity,
            )
        )
        order += 1

    if cooldown_m > 0:
        steps.append(cooldown_step(cooldown_km, step_order=order))

    return steps


def _build_steps(workout: Workout) -> list[dict]:
    """Dispatch to the correct step builder based on workout_type."""
    wtype = workout.workout_type.lower().strip()

    # --- styrktaræfing (strength) ---
    if wtype == "styrktaræfing":
        return [_strength_step()]

    # --- Types with defined warmup/cooldown templates ---
    if wtype in STEP_TEMPLATES:
        tmpl = STEP_TEMPLATES[wtype]
        pace = PACE_TARGETS.get(wtype)

        # hraðaæf uses INTERVAL intensity for the active portion
        intensity = "INTERVAL" if wtype == "hraðaæf" else "ACTIVE"

        return _build_running_steps(
            workout,
            warmup_km=tmpl["warmup_km"],
            cooldown_km=tmpl["cooldown_km"],
            pace_target=pace,
            active_intensity=intensity,
        )

    # --- Fallback: "other" — single active step, full distance, no target ---
    if workout.distance_km > 0:
        return [active_step(workout.distance_km, step_order=1)]
    return [_strength_step()]  # Zero-distance unknown → lap button press


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_workout_json(workout: Workout) -> dict:
    """Convert a parsed Workout into Garmin Connect workout JSON.

    Returns:
        A dict matching the Garmin Connect workout upload schema, ready to be
        serialised to JSON and passed to ``garminconnect.upload_workout()``.
    """
    wtype = workout.workout_type.lower().strip()

    # Pick sport type
    if wtype == "styrktaræfing":
        sport = {**STRENGTH_SPORT}
    else:
        sport = {**RUNNING_SPORT}

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
