"""
Uploads upcoming events from data/upcoming_events.json to Supabase.
Run after upload_events.py so IDs continue from past events.

Usage:
  python upload_upcoming_events.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

INPUT_FILE = Path(__file__).parent / "data" / "upcoming_events.json"


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    with open(INPUT_FILE) as f:
        data = json.load(f)

    events = data["events"]
    print(f"Uploading {len(events)} upcoming events...\n")

    for event in events:
        row = {
            "name":       event["name"],
            "url":        event["url"],
            "logo_url":   event["logo_url"],
            "city":       event["city"] or None,
            "country":    event["country"] or None,
            "start_date": event["start_date"],
            "end_date":   event["end_date"],
        }
        result = supabase.table("events").insert(row).execute()
        inserted_id = result.data[0]["id"] if result.data else "?"
        print(f"  [{inserted_id}] {row['name']} ({row['start_date']} → {row['end_date']})")

    print(f"\nDone. {len(events)} upcoming events uploaded.")


if __name__ == "__main__":
    main()
