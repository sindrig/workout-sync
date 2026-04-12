"""Download actual distances from Garmin Connect and write them into the XLS."""

from __future__ import annotations

import datetime
import struct
from collections import defaultdict
from pathlib import Path

import olefile
from xlwt.CompoundDoc import XlsDoc

from .garmin_client import GarminClient
from .parser import WorkoutRow

_ACTUAL_KM_COL = 4  # 0-indexed, column E in the spreadsheet

# BIFF8 record opcodes
_BIFF_BOF = 0x0809
_BIFF_BOUNDSHEET = 0x0085
_BIFF_BLANK = 0x0201
_BIFF_NUMBER = 0x0203
_BIFF_RK = 0x027E
_BIFF_MULRK = 0x00BD
_BIFF_MULBLANK = 0x00BE


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


def _read_biff_stream(xls_path: Path) -> bytes:
    ole = olefile.OleFileIO(str(xls_path))  # type: ignore[arg-type]
    try:
        return ole.openstream("Workbook").read()
    finally:
        ole.close()


def _patch_biff_stream(data: bytes, edits: dict[tuple[int, int], float]) -> bytes:
    """Patch a BIFF8 Workbook stream, replacing BLANK/MULBLANK cells with NUMBER.

    Every record that is NOT a target cell is copied byte-for-byte — formulas,
    formatting, images, everything survives untouched.  BOUNDSHEET pointers are
    recalculated after patching so the sheet BOF offsets remain valid.
    """
    if not edits:
        return data

    # --- Locate structural landmarks ---
    bof_positions: list[int] = []
    boundsheet_positions: list[int] = []
    pos = 0
    while pos < len(data) - 4:
        opcode, length = struct.unpack_from("<HH", data, pos)
        if opcode == _BIFF_BOF:
            bof_positions.append(pos)
        pos += 4 + length

    if len(bof_positions) < 2:
        return data

    globals_end = bof_positions[1]

    # Find BOUNDSHEET records within Globals substream
    pos = 0
    while pos < globals_end:
        opcode, length = struct.unpack_from("<HH", data, pos)
        if opcode == _BIFF_BOUNDSHEET:
            boundsheet_positions.append(pos)
        pos += 4 + length

    # --- Determine which segment (sheet) contains each edit ---
    # Build segment boundaries: [globals_end, sheet2_bof, sheet3_bof, ..., len(data)]
    seg_boundaries = bof_positions[1:] + [len(data)]
    # Only patch the segment that contains target cells (typically Sheet1).
    # For safety, figure out which sheet index each edit falls in by scanning
    # the original data for BLANK/MULBLANK records.
    patch_segments: set[int] = set()
    pos = 0
    while pos < len(data) - 4:
        opcode, length = struct.unpack_from("<HH", data, pos)
        rec_data = data[pos + 4 : pos + 4 + length]

        seg_idx = _segment_for_offset(pos, seg_boundaries)

        if opcode in (_BIFF_BLANK, _BIFF_NUMBER, _BIFF_RK) and length >= 6:
            row, col = struct.unpack_from("<HH", rec_data)
            if (row, col) in edits:
                patch_segments.add(seg_idx)

        elif opcode in (_BIFF_MULBLANK, _BIFF_MULRK) and length >= 6:
            row, first_col = struct.unpack_from("<HH", rec_data)
            last_col = struct.unpack_from("<H", rec_data, length - 2)[0]
            for c in range(first_col, last_col + 1):
                if (row, c) in edits:
                    patch_segments.add(seg_idx)

        pos += 4 + length

    # --- Rebuild stream ---
    output = bytearray()
    new_bof_offsets: dict[int, int] = {}

    # Copy Globals verbatim (track BOUNDSHEET output positions for fixup)
    bs_output_positions: list[int] = []
    pos = 0
    while pos < globals_end:
        opcode, length = struct.unpack_from("<HH", data, pos)
        if opcode == _BIFF_BOUNDSHEET:
            bs_output_positions.append(len(output))
        output += data[pos : pos + 4 + length]
        pos += 4 + length

    # Copy each sheet segment
    for seg_idx in range(len(seg_boundaries) - 1):
        seg_start = seg_boundaries[seg_idx]
        seg_end = seg_boundaries[seg_idx + 1]
        new_bof_offsets[seg_idx] = len(output)

        if seg_idx not in patch_segments:
            output += data[seg_start:seg_end]
            continue

        # Patch this segment record by record
        pos = seg_start
        while pos < seg_end:
            opcode, length = struct.unpack_from("<HH", data, pos)
            rec_data = data[pos + 4 : pos + 4 + length]
            rec_end = pos + 4 + length

            if opcode in (_BIFF_BLANK, _BIFF_NUMBER, _BIFF_RK) and length >= 6:
                row, col, xf_idx = struct.unpack_from("<HHH", rec_data)
                if (row, col) in edits:
                    output += struct.pack(
                        "<HHHHH d",
                        _BIFF_NUMBER,
                        14,
                        row,
                        col,
                        xf_idx,
                        edits[(row, col)],
                    )
                    pos = rec_end
                    continue

            elif opcode == _BIFF_MULBLANK and length >= 6:
                row, first_col = struct.unpack_from("<HH", rec_data)
                last_col = struct.unpack_from("<H", rec_data, length - 2)[0]

                if any((row, c) in edits for c in range(first_col, last_col + 1)):
                    for i in range(last_col - first_col + 1):
                        c = first_col + i
                        xf_idx = struct.unpack_from("<H", rec_data, 4 + i * 2)[0]
                        if (row, c) in edits:
                            output += struct.pack(
                                "<HHHHH d",
                                _BIFF_NUMBER,
                                14,
                                row,
                                c,
                                xf_idx,
                                edits[(row, c)],
                            )
                        else:
                            output += struct.pack(
                                "<HHHHH", _BIFF_BLANK, 6, row, c, xf_idx
                            )
                    pos = rec_end
                    continue

            elif opcode == _BIFF_MULRK and length >= 6:
                row, first_col = struct.unpack_from("<HH", rec_data)
                last_col = struct.unpack_from("<H", rec_data, length - 2)[0]

                if any((row, c) in edits for c in range(first_col, last_col + 1)):
                    # MULRK packs (xf_idx: 2 bytes, rk_value: 4 bytes) per cell
                    for i in range(last_col - first_col + 1):
                        c = first_col + i
                        xf_idx = struct.unpack_from("<H", rec_data, 4 + i * 6)[0]
                        if (row, c) in edits:
                            output += struct.pack(
                                "<HHHHH d",
                                _BIFF_NUMBER,
                                14,
                                row,
                                c,
                                xf_idx,
                                edits[(row, c)],
                            )
                        else:
                            rk_val = struct.unpack_from("<I", rec_data, 6 + i * 6)[0]
                            output += struct.pack(
                                "<HHHHI", _BIFF_RK, 10, row, c, xf_idx
                            )
                            output += struct.pack("<I", rk_val)
                    pos = rec_end
                    continue

            output += data[pos:rec_end]
            pos = rec_end

    # Handle the last segment (after last boundary)
    last_seg_start = seg_boundaries[-1]
    if last_seg_start < len(data):
        new_bof_offsets[len(seg_boundaries) - 1] = len(output)
        output += data[last_seg_start:]

    # --- Fix BOUNDSHEET offsets ---
    for i, bs_pos in enumerate(bs_output_positions):
        if i < len(new_bof_offsets):
            struct.pack_into("<L", output, bs_pos + 4, new_bof_offsets[i])

    return bytes(output)


def _segment_for_offset(pos: int, boundaries: list[int]) -> int:
    for i, boundary in enumerate(boundaries):
        if pos < boundary:
            return i - 1 if i > 0 else 0
    return len(boundaries) - 1


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
    edits: dict[tuple[int, int], float] = {}
    written: list[tuple[WorkoutRow, float]] = []

    for row in rows:
        raw_km = distances.get(row.date)
        if raw_km is None:
            continue
        rounded = round_to_increment(raw_km, increment)
        edits[(row.row_idx, _ACTUAL_KM_COL)] = rounded
        written.append((row, rounded))

    if edits:
        biff = _read_biff_stream(xls_path)
        patched = _patch_biff_stream(biff, edits)
        XlsDoc().save(str(xls_path), patched)

    return written
