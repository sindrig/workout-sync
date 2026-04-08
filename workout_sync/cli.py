"""CLI module for workout_sync."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .builder import build_workout_json
from .downloader import fetch_actual_distances, round_to_increment, write_actual_km
from .garmin_client import GarminClient
from .parser import parse_xls, parse_xls_rows


def main():
    parser = argparse.ArgumentParser(
        prog="workout-sync",
        description="Sync workouts between XLS training plan and Garmin Connect",
    )
    subparsers = parser.add_subparsers(dest="command")

    upload_parser = subparsers.add_parser(
        "upload", help="Upload workout plan from XLS to Garmin Connect"
    )
    upload_parser.add_argument(
        "xls_file", type=str, help="Path to the XLS workout plan file"
    )
    upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display workouts without uploading",
    )

    download_parser = subparsers.add_parser(
        "download",
        help="Pull actual distances from Garmin Connect into the XLS",
    )
    download_parser.add_argument(
        "xls_file", type=str, help="Path to the XLS workout plan file"
    )
    download_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without modifying the file",
    )
    download_parser.add_argument(
        "--increment",
        type=float,
        default=0.5,
        help="Distance rounding increment in km (default: 0.5)",
    )

    args = parser.parse_args()

    # Default to upload when no subcommand given (backward compat)
    if args.command is None:
        args = upload_parser.parse_args()
        args.command = "upload"

    xls_path = Path(args.xls_file).expanduser()
    if not xls_path.exists():
        print(f"Error: File not found: {args.xls_file}", file=sys.stderr)
        sys.exit(1)

    load_dotenv()

    if args.command == "upload":
        _upload_command(xls_path, args)
    elif args.command == "download":
        _download_command(xls_path, args)


def _upload_command(xls_path: Path, args: argparse.Namespace):
    try:
        workouts = parse_xls(str(xls_path))
    except Exception as e:
        print(f"Error parsing XLS file: {e}", file=sys.stderr)
        sys.exit(1)

    if not workouts:
        print("No workouts found in the XLS file.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        _upload_dry_run(workouts)
    else:
        _upload_live(workouts)


def _upload_dry_run(workouts: list):
    print("=== DRY RUN ===\n")

    total_km = 0.0
    for w in workouts:
        w_json = build_workout_json(w)
        steps = w_json["workoutSegments"][0]["workoutSteps"]

        print(
            f"{w.date.strftime('%Y-%m-%d')} ({w.day_name}) {w.workout_type}: {w.description} [{w.distance_km} km]"
        )
        for step in steps:
            step_name = step["stepType"]["stepTypeKey"].capitalize()
            end_cond = step["endCondition"]["conditionTypeKey"]

            if end_cond == "distance":
                dist_km = (step.get("endConditionValue") or 0) / 1000.0
            else:
                dist_km = 0.0

            target_key = step["targetType"]["workoutTargetTypeKey"]

            if target_key == "pace.zone":
                slow_ms = step["targetValueOne"]
                fast_ms = step["targetValueTwo"]
                sec_per_km_fast = 1000.0 / fast_ms
                sec_per_km_slow = 1000.0 / slow_ms
                min_fast = int(round(sec_per_km_fast) // 60)
                sec_fast = int(round(sec_per_km_fast) % 60)
                min_slow = int(round(sec_per_km_slow) // 60)
                sec_slow = int(round(sec_per_km_slow) % 60)
                print(
                    f"  → {step_name}: {dist_km:.1f} km @ ~{min_fast}:{sec_fast:02d}-{min_slow}:{sec_slow:02d}/km"
                )
            elif end_cond == "lap.button":
                print(f"  → {step_name}: open-ended")
            else:
                print(f"  → {step_name}: {dist_km:.1f} km")

        total_km += w.distance_km

    print(f"\nTotal: {len(workouts)} workouts, {total_km:.1f} km")


def _upload_live(workouts: list):
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        print(
            "Error: Missing credentials. Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=== GARMIN CONNECT UPLOAD ===\n")

    workouts_to_upload = []
    for w in workouts:
        w_json = build_workout_json(w)
        date_str = w.date.strftime("%Y-%m-%d")
        workouts_to_upload.append((w_json, date_str))

    print(f"Plan: {len(workouts)} workouts")
    for w_json, date_str in workouts_to_upload:
        name = w_json.get("workoutName", "?")
        print(f"  {date_str} {name}")
    print()

    try:
        print("Logging in to Garmin Connect...")
        client = GarminClient(email, password)
        client.login()
        print("✓ Login successful\n")
    except Exception as e:
        print(f"Error authenticating to Garmin Connect: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        client.delete_workouts_by_prefix("[WS]")
        print()
    except Exception as e:
        print(f"Warning: Failed to delete existing workouts: {e}", file=sys.stderr)
        print()

    try:
        client.upload_all(workouts_to_upload)
    except Exception as e:
        print(f"Error uploading workouts: {e}", file=sys.stderr)
        sys.exit(1)


def _download_command(xls_path: Path, args: argparse.Namespace):
    try:
        rows = parse_xls_rows(str(xls_path))
    except Exception as e:
        print(f"Error parsing XLS file: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No workout rows found in the XLS file.", file=sys.stderr)
        sys.exit(1)

    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        print(
            "Error: Missing credentials. Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        print("Logging in to Garmin Connect...")
        client = GarminClient(email, password)
        client.login()
        print("✓ Login successful\n")
    except Exception as e:
        print(f"Error authenticating to Garmin Connect: {e}", file=sys.stderr)
        sys.exit(1)

    print("Fetching activities from Garmin Connect...")
    try:
        distances = fetch_actual_distances(client, rows)
    except Exception as e:
        print(f"Error fetching activities: {e}", file=sys.stderr)
        sys.exit(1)

    if not distances:
        print("No running activities found for the plan dates.")
        return

    increment = args.increment

    print(
        f"\n=== {'DRY RUN — ' if args.dry_run else ''}KM Í RAUN (increment: {increment} km) ===\n"
    )

    matched = 0
    for row in rows:
        raw_km = distances.get(row.date)
        if raw_km is None:
            continue
        rounded = round_to_increment(raw_km, increment)
        delta = rounded - row.distance_km if row.distance_km else None
        delta_str = f" (Δ {delta:+.1f})" if delta is not None else ""
        print(
            f"  {row.date.isoformat()} ({row.day_name}) {row.description[:40]:<40}  "
            f"plan: {row.distance_km:5.1f} km  actual: {rounded:5.1f} km{delta_str}"
        )
        matched += 1

    unmatched = len(rows) - matched
    print(f"\n{matched} day(s) with activity data, {unmatched} without.")

    if args.dry_run:
        print("\nDry run — no files modified.")
        return

    try:
        written = write_actual_km(xls_path, rows, distances, increment)
    except Exception as e:
        print(f"Error writing to XLS: {e}", file=sys.stderr)
        sys.exit(1)

    xlsx_path = xls_path.with_suffix(".xlsx")
    print(f"\n✓ Wrote {len(written)} value(s) to {xlsx_path}")
