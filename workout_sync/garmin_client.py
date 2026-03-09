"""Garmin Connect API client for uploading, scheduling, and deleting workouts."""

from __future__ import annotations

import os
from pathlib import Path

from garminconnect import Garmin


GARTH_TOKEN_DIR = os.path.expanduser("~/.garth")


class GarminClient:
    def __init__(self, email: str, password: str):
        self.client = Garmin(email, password, prompt_mfa=self._prompt_mfa)

    @staticmethod
    def _prompt_mfa() -> str:
        return input("Enter MFA code: ")

    def login(self):
        token_dir = GARTH_TOKEN_DIR
        try:
            self.client.login(tokenstore=token_dir)
        except Exception:
            self.client.login()
        Path(token_dir).mkdir(parents=True, exist_ok=True)
        self.client.garth.dump(token_dir)

    def delete_workouts_by_prefix(self, prefix: str = "[WS]") -> int:
        workouts = self._get_all_workouts()
        to_delete = [w for w in workouts if w.get("workoutName", "").startswith(prefix)]

        deleted = 0
        for w in to_delete:
            workout_id = w["workoutId"]
            try:
                self.client.garth.request(
                    "DELETE",
                    "connectapi",
                    f"/workout-service/workout/{workout_id}",
                    api=True,
                )
                deleted += 1
            except Exception as e:
                print(f"  Failed to delete workout {workout_id}: {e}")

        print(f"Deleted {deleted} existing [WS] workout(s)")
        return deleted

    def _get_all_workouts(self) -> list[dict]:
        all_workouts: list[dict] = []
        start = 0
        batch_size = 100

        while True:
            # get_workouts is typed as dict but actually returns a list
            batch: list[dict] = self.client.get_workouts(start=start, limit=batch_size)  # type: ignore[assignment]
            if not batch:
                break
            all_workouts.extend(batch)
            if len(batch) < batch_size:
                break
            start += batch_size

        return all_workouts

    def upload_and_schedule(self, workout_json: dict, date_str: str) -> dict:
        result = self.client.upload_workout(workout_json)
        workout_id = result["workoutId"]

        self.client.garth.post(
            "connectapi",
            f"/workout-service/schedule/{workout_id}",
            json={"date": date_str},
            api=True,
        )

        return result

    def upload_all(self, workouts: list[tuple[dict, str]]):
        uploaded = 0
        failed = 0

        for workout_json, date_str in workouts:
            name = workout_json.get("workoutName", "?")
            try:
                self.upload_and_schedule(workout_json, date_str)
                uploaded += 1
                print(f"  ✓ {date_str} {name}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {date_str} {name}: {e}")

        print(f"\nUploaded {uploaded} workout(s). {failed} failed.")
