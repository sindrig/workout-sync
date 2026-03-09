"""CLI module for workout_sync."""

import argparse


def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="workout-sync", description="Sync workouts from Garmin Connect"
    )
    parser.add_argument("xls_file", type=str, help="Path to XLS file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without uploading"
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    args = parser.parse_args()
    print("Workout Sync CLI - Not implemented yet")
