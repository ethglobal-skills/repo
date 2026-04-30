"""
Uploads events from data/events.json to Supabase.
Events are inserted oldest-first so ETHWaterloo gets id=1.

Usage:
  cp .env.example .env  # fill in your keys
  python upload_events.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

INPUT_FILE = Path(__file__).parent / "data" / "events.json"


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    with open(INPUT_FILE) as f:
        data = json.load(f)

    # Sort oldest → newest so serial IDs reflect chronological order
    events = sorted(
        data["events"],
        key=lambda e: e.get("start_date") or "0000-00-00",
    )

    print(f"Uploading {len(events)} events (oldest first)...\n")

    for event in events:
        row = {
            "name":       event.get("name", ""),
            "url":        event.get("url", ""),
            "logo_url":   event.get("logo_url", ""),
            "city":       event.get("city") or None,
            "country":    event.get("country") or None,
            "start_date": event.get("start_date") or None,
            "end_date":   event.get("end_date") or None,
        }
        result = supabase.table("events").insert(row).execute()
        inserted_id = result.data[0]["id"] if result.data else "?"
        print(f"  [{inserted_id}] {row['name']} ({row['start_date']})")

    print(f"\nDone. {len(events)} events uploaded.")


if __name__ == "__main__":
    main()
