"""Download actual distances from Garmin Connect and write them into the XLS."""

from __future__ import annotations

import datetime
from collections import defaultdict
from pathlib import Path

import xlrd
from xlutils.copy import copy as xlutils_copy

from .garmin_client import GarminClient
from .parser import WorkoutRow

_ACTUAL_KM_COL = 4  # 0-indexed, column E in the spreadsheet


def round_to_increment(value: float, increment: float) -> float:
    """Round value to the nearest multiple of increment.

    >>> round_to_increment(9.73, 0.5)
    9.5
    >>> round_to_increment(9.75, 0.5)
    10.0
    >>> round_to_increment(10.26, 0.5)
    10.5
    """
    return round(value / increment) * increment


def _build_date_distance_map(
    activities: list[dict],
) -> dict[datetime.date, float]:
    """Sum running distances per date from Garmin activity list.

    Activities have distance in meters and startTimeLocal as ISO string.
    """
    totals: dict[datetime.date, float] = defaultdict(float)
    for activity in activities:
        distance_m = activity.get("distance", 0) or 0
        start_local = activity.get("startTimeLocal", "")
        if not start_local or distance_m <= 0:
            continue
        date = datetime.date.fromisoformat(start_local[:10])
        totals[date] += distance_m / 1000.0
    return dict(totals)


def fetch_actual_distances(
    client: GarminClient,
    rows: list[WorkoutRow],
) -> dict[datetime.date, float]:
    if not rows:
        return {}

    start = min(r.date for r in rows)
    end = max(r.date for r in rows)
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    return _build_date_distance_map(activities)


def write_actual_km(
    xls_path: Path,
    rows: list[WorkoutRow],
    distances: dict[datetime.date, float],
    increment: float,
) -> list[tuple[WorkoutRow, float]]:
    # xlutils.copy preserves formatting; xlrd must open with formatting_info=True
    rb = xlrd.open_workbook(str(xls_path), formatting_info=True)
    wb = xlutils_copy(rb)
    ws = wb.get_sheet(0)

    written: list[tuple[WorkoutRow, float]] = []

    for row in rows:
        raw_km = distances.get(row.date)
        if raw_km is None:
            continue

        rounded = round_to_increment(raw_km, increment)
        ws.write(row.row_idx, _ACTUAL_KM_COL, rounded)
        written.append((row, rounded))

    wb.save(str(xls_path))
    return written
