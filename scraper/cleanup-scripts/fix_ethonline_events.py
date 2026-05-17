"""
Fixes ETHOnline and HackMoney projects in Supabase that have the wrong event_id.

Source of truth: data/projects_raw.json (has correct event name per project URL).
The upload script's fuzzy year-stripping caused all variants of a series to map
to whichever event was matched first (e.g. all ETHOnline → ETHOnline 2025,
all HackMoney → HackMoney 2026).

This script:
  1. Loads affected projects from the JSON (url + correct event name)
  2. Builds an exact event name → event_id lookup from Supabase
  3. For each project, finds it in Supabase by URL, checks its event_id
  4. If wrong, updates it to the correct event_id

Usage:
  python fix_ethonline_events.py           # dry run
  python fix_ethonline_events.py --apply   # write to Supabase
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

INPUT_FILE = Path(__file__).parent / "data" / "projects_raw.json"


def main():
    apply = "--apply" in sys.argv

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    if not apply:
        print("DRY RUN — pass --apply to write changes\n")

    # Load JSON source of truth
    with open(INPUT_FILE) as f:
        data = json.load(f)

    SERIES = ["new york", "nfthack"]

    target_projects = [
        p for p in data["projects"]
        if any(s in p.get("event", "").lower() for s in SERIES)
    ]
    print(f"Target projects in JSON: {len(target_projects)}")

    # Build exact name → event_id lookup from Supabase
    events_result = supabase.table("events").select("id, name").execute()
    event_name_to_id = {row["name"]: row["id"] for row in events_result.data}

    target_event_ids = {
        name: eid for name, eid in event_name_to_id.items()
        if any(s in name.lower() for s in SERIES)
    }
    print(f"Matched events in Supabase: {target_event_ids}\n")

    # Iterate JSON projects in batches, look each up in Supabase by URL
    BATCH_SIZE = 200
    corrections = 0
    skipped = 0
    not_found = 0

    for batch_start in range(0, len(target_projects), BATCH_SIZE):
        batch = target_projects[batch_start: batch_start + BATCH_SIZE]
        urls = [p["url"] for p in batch if p.get("url")]

        db_result = supabase.table("projects").select("id, url, event_id").in_("url", urls).execute()
        db_by_url = {row["url"]: row for row in db_result.data}

        for project in batch:
            url = project.get("url", "")
            correct_event_name = project.get("event", "")
            correct_event_id = event_name_to_id.get(correct_event_name)

            if not correct_event_id:
                print(f"  ! No event_id for '{correct_event_name}' — skipping {project['title']!r}")
                skipped += 1
                continue

            db_row = db_by_url.get(url)
            if not db_row:
                not_found += 1
                continue

            if db_row["event_id"] == correct_event_id:
                continue

            current_event_name = next(
                (name for name, eid in event_name_to_id.items() if eid == db_row["event_id"]),
                str(db_row["event_id"]),
            )
            print(
                f"  {'UPDATING' if apply else 'WOULD UPDATE'}: {project['title']!r}\n"
                f"    {current_event_name!r} → {correct_event_name!r}"
            )

            if apply:
                supabase.table("projects").update({"event_id": correct_event_id}).eq("id", db_row["id"]).execute()

            corrections += 1

        print(f"  Processed batch {batch_start // BATCH_SIZE + 1} ({batch_start + len(batch)}/{len(target_projects)})")

    print(f"\n--- Summary ---")
    print(f"Corrections: {corrections}")
    print(f"Not in Supabase: {not_found}")
    print(f"Skipped (unknown event name): {skipped}")

    if corrections and not apply:
        print("\nRe-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
