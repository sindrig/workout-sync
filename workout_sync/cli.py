"""CLI module for workout_sync."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .builder import build_workout_json
from .garmin_client import GarminClient
from .parser import parse_xls


def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="workout-sync",
        description="Upload workout plan from XLS to Garmin Connect",
    )
    parser.add_argument("xls_file", type=str, help="Path to the XLS workout plan file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display workouts without uploading",
    )
    args = parser.parse_args()

    # Validate XLS file exists
    xls_path = Path(args.xls_file).expanduser()
    if not xls_path.exists():
        print(f"Error: File not found: {args.xls_file}", file=sys.stderr)
        sys.exit(1)

    # Load .env if present
    load_dotenv()

    # Parse workouts
    try:
        workouts = parse_xls(str(xls_path))
    except Exception as e:
        print(f"Error parsing XLS file: {e}", file=sys.stderr)
        sys.exit(1)

    if not workouts:
        print("No workouts found in the XLS file.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        _dry_run_flow(workouts)
    else:
        _normal_flow(workouts)


def _dry_run_flow(workouts: list):
    """Dry-run mode: parse XLS, build JSONs, print structured summary."""
    print("=== DRY RUN ===\n")

    total_km = 0.0
    for w in workouts:
        w_json = build_workout_json(w)
        steps = w_json["workoutSegments"][0]["workoutSteps"]

        print(
            f"{w.date.strftime('%Y-%m-%d')} ({w.day_name}) {w.workout_type}: {w.description} [{w.distance_km} km]"
        )
        for step in steps:
            step_name = step["intensity"].capitalize()
            dist_m = step.get("durationValue", 0)
            dist_km = dist_m / 1000.0 if dist_m else 0.0

            if step["targetType"] == "PACE":
                low_ms = step["targetValueOne"]
                high_ms = step["targetValueTwo"]
                sec_per_km_low = 1000.0 / high_ms  # faster = higher m/s
                sec_per_km_high = 1000.0 / low_ms  # slower = lower m/s
                min_low = int(sec_per_km_low // 60)
                sec_low = int(sec_per_km_low % 60)
                min_high = int(sec_per_km_high // 60)
                sec_high = int(sec_per_km_high % 60)
                print(
                    f"  → {step_name}: {dist_km:.1f} km @ ~{min_low}:{sec_low:02d}-{min_high}:{sec_high:02d}/km"
                )
            elif step["durationType"] == "LAP_BUTTON_PRESS":
                print(f"  → {step_name}: open-ended")
            else:
                print(f"  → {step_name}: {dist_km:.1f} km")

        total_km += w.distance_km

    print(f"\nTotal: {len(workouts)} workouts, {total_km:.1f} km")


def _normal_flow(workouts: list):
    """Normal flow: load env, login, delete existing, upload + schedule all."""
    # Load credentials from environment
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        print(
            "Error: Missing credentials. Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=== GARMIN CONNECT UPLOAD ===\n")

    # Build (workout_json, date_str) tuples
    workouts_to_upload = []
    for w in workouts:
        w_json = build_workout_json(w)
        date_str = w.date.strftime("%Y-%m-%d")
        workouts_to_upload.append((w_json, date_str))

    # Print summary
    print(f"Plan: {len(workouts)} workouts")
    for w_json, date_str in workouts_to_upload:
        name = w_json.get("workoutName", "?")
        print(f"  {date_str} {name}")
    print()

    # Initialize client and login
    try:
        print("Logging in to Garmin Connect...")
        client = GarminClient(email, password)
        client.login()
        print("✓ Login successful\n")
    except Exception as e:
        print(f"Error authenticating to Garmin Connect: {e}", file=sys.stderr)
        sys.exit(1)

    # Delete existing [WS] workouts
    try:
        client.delete_workouts_by_prefix("[WS]")
        print()
    except Exception as e:
        print(f"Warning: Failed to delete existing workouts: {e}", file=sys.stderr)
        print()

    # Upload and schedule all
    try:
        client.upload_all(workouts_to_upload)
    except Exception as e:
        print(f"Error uploading workouts: {e}", file=sys.stderr)
        sys.exit(1)
