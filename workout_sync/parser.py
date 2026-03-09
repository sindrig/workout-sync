"""Parser module for coach's workout training plan XLS files (Icelandic format)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import xlrd


@dataclass
class Workout:
    """A single workout entry from the training plan."""

    date: datetime.date
    day_name: str
    workout_type: str
    description: str
    distance_km: float
    notes: str


def _classify_workout_type(description: str) -> str:
    """Classify workout type from Icelandic description text.

    Order matters — check more specific terms before general ones.
    """
    desc_lower = description.lower()

    if "ról" in desc_lower:
        return "ról"
    if "hraðaæf" in desc_lower:
        return "hraðaæf"
    if "jafnt" in desc_lower:
        return "jafnt"
    if "samæfing" in desc_lower:
        return "samæfing"
    if "styrktaræfing" in desc_lower:
        return "styrktaræfing"
    if "fartleikur" in desc_lower or "fartleik" in desc_lower:
        return "fartleikur"
    if "Hlaupasería" in description:
        return "samæfing"
    return "other"


def parse_xls(filepath: str) -> list[Workout]:
    """Parse coach's workout XLS file and extract non-rest workout days.

    Args:
        filepath: Path to the XLS file.

    Returns:
        List of Workout entries sorted by date ascending, with rest days excluded.
    """
    wb = xlrd.open_workbook(filepath)
    sheet = wb.sheet_by_index(0)

    workouts: list[Workout] = []

    # Data rows start at row 8 (rows 0-7 are headers)
    for row_idx in range(8, sheet.nrows):
        # Only process rows where column 0 is a date (ctype == 3)
        if sheet.cell_type(row_idx, 0) != xlrd.XL_CELL_DATE:
            continue

        # Decode Excel date serial to Python date
        date_value = float(sheet.cell_value(row_idx, 0))
        date_tuple = xlrd.xldate_as_tuple(date_value, wb.datemode)
        date = datetime.date(*date_tuple[:3])

        # Extract fields
        day_name = str(sheet.cell_value(row_idx, 1)).strip()
        description = str(sheet.cell_value(row_idx, 2)).strip()
        distance_km = (
            float(sheet.cell_value(row_idx, 3))
            if sheet.cell_type(row_idx, 3) == xlrd.XL_CELL_NUMBER
            else 0.0
        )
        notes = str(sheet.cell_value(row_idx, 5)).strip()

        # Classify workout type
        workout_type = _classify_workout_type(description)

        # Skip rest days: 0 km AND not a strength workout
        if distance_km == 0.0 and workout_type != "styrktaræfing":
            continue

        workouts.append(
            Workout(
                date=date,
                day_name=day_name,
                workout_type=workout_type,
                description=description,
                distance_km=distance_km,
                notes=notes,
            )
        )

    # Sort by date ascending
    workouts.sort(key=lambda w: w.date)

    return workouts
