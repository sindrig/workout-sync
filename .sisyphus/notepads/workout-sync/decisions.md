# Decisions — Workout Sync

## Architectural Choices

### Task 3: Builder JSON Schema Format
- **Decision**: Used simplified field names (intensity/durationType/targetType as plain strings) per task spec schema
- **Rationale**: Task spec explicitly defined the schema. Real Garmin API uses ExecutableStepDTO with nested dicts for stepType/endCondition/targetType. A mapping layer can be added later if needed for actual upload.
- **Risk**: May need transformation before passing to `garminconnect.upload_workout()`. The garmin_client module can handle this mapping.

### Task 3: Workout Dataclass Location
- **Decision**: Defined `Workout` dataclass locally in builder.py (not imported from parser)
- **Rationale**: Task 2 (parser) runs in parallel and may not be merged yet. Local definition ensures builder is self-contained. Will consolidate when both tasks land.

### Task 3: Negative Distance Handling
- **Decision**: Proportionally scale warmup/cooldown when total < warmup+cooldown, rather than error
- **Rationale**: Graceful degradation is better for training plans with short distances. A 1km "ról" still gets a warmup/cooldown structure, just scaled down.
