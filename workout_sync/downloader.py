"""Download actual distances from Garmin Connect and write them into the XLS."""

from __future__ import annotations

import datetime
import struct
from collections import defaultdict
from pathlib import Path

import xlrd
import xlwt
from xlutils.copy import copy as xlutils_copy

from .garmin_client import GarminClient
from .parser import WorkoutRow

_ACTUAL_KM_COL = 4  # 0-indexed, column E in the spreadsheet


def _col_letter(col_idx: int) -> str:
    """Convert 0-based column index to Excel column letter (0→A, 3→D, 4→E)."""
    result = ""
    idx = col_idx
    while True:
        result = chr(ord("A") + idx % 26) + result
        idx = idx // 26 - 1
        if idx < 0:
            break
    return result


def _extract_formulas(xls_path: Path) -> list[tuple[int, int, str]]:
    """Extract formula cells from XLS BIFF records.

    Returns list of (row, col, formula_text) for every FORMULA record found
    in sheet 0.  Only SUM() with a single area argument is decoded — that
    covers the weekly-total rows in the coach's spreadsheet.
    """
    try:
        import olefile

        ole = olefile.OleFileIO(str(xls_path))  # type: ignore[arg-type]
        try:
            data = ole.openstream("Workbook").read()
        finally:
            ole.close()
    except ImportError:
        import io

        doc = xlrd.compdoc.CompDoc(str(xls_path), logfile=io.StringIO())  # type: ignore[attr-defined]
        data = doc.get_named_stream("Workbook")

    formulas: list[tuple[int, int, str]] = []
    pos = 0
    while pos < len(data) - 4:
        opcode = struct.unpack("<H", data[pos : pos + 2])[0]
        length = struct.unpack("<H", data[pos + 2 : pos + 4])[0]

        if opcode == 0x0006 and length >= 22:  # FORMULA record
            rec = data[pos + 4 : pos + 4 + length]
            row, col = struct.unpack("<HH", rec[0:4])
            formula_size = struct.unpack("<H", rec[20:22])[0]
            tokens = rec[22 : 22 + formula_size]

            formula_text = _decode_formula_tokens(tokens)
            if formula_text is not None:
                formulas.append((row, col, formula_text))

        pos += 4 + length
        if pos >= len(data):
            break

    return formulas


def _decode_formula_tokens(tokens: bytes) -> str | None:
    """Best-effort decode of BIFF8 formula tokens.

    Handles the common case: ``SUM(<area>)`` with a single tArea2d operand,
    encoded either via tAttrSum (optimised single-arg SUM) or tFuncVar.
    Returns the formula string (without leading ``=``) or *None* if the
    tokens cannot be decoded.
    """
    if len(tokens) < 9:
        return None

    first_token = tokens[0]
    # tArea2d variants: 0x25 (tAreaR), 0x45 (tAreaV), 0x65 (tAreaA)
    if first_token not in (0x25, 0x45, 0x65):
        return None

    first_row, last_row, first_col_raw, last_col_raw = struct.unpack(
        "<HHHH", tokens[1:9]
    )
    first_col = first_col_raw & 0x00FF
    last_col = last_col_raw & 0x00FF

    area_ref = (
        f"{_col_letter(first_col)}{first_row + 1}:{_col_letter(last_col)}{last_row + 1}"
    )

    rest = tokens[9:]
    t = 0
    while t < len(rest):
        tid = rest[t]
        if tid == 0x19:  # tAttr
            if t + 1 < len(rest) and (rest[t + 1] & 0x10):
                # tAttrSum — optimised single-arg SUM
                return f"SUM({area_ref})"
            t += 4  # tAttr is always 4 bytes in BIFF8
            continue
        if tid in (0x42, 0x62, 0x82):  # tFuncVar
            if t + 4 <= len(rest):
                func_idx = struct.unpack("<H", rest[t + 2 : t + 4])[0]
                if func_idx == 4:
                    return f"SUM({area_ref})"
            return None
        if tid in (0x41, 0x61, 0x81):  # tFunc
            if t + 3 <= len(rest):
                func_idx = struct.unpack("<H", rest[t + 1 : t + 3])[0]
                if func_idx == 4:
                    return f"SUM({area_ref})"
            return None
        break

    return None


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
    formulas = _extract_formulas(xls_path)

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

    for formula_row, formula_col, formula_text in formulas:
        ws.write(formula_row, formula_col, xlwt.Formula(formula_text))

    wb.save(str(xls_path))
    return written
