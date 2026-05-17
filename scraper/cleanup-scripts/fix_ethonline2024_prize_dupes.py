"""
Merges duplicate prizes at ETHOnline 2024.

Two prize records exist per award due to double scraping:
  - Canonical (from event page): clean title, has description, no placement
  - Project-derived (from project pages): title with placement (1st/2nd/3rd), no description

Goal: end up with one prize per award that has BOTH the placement title AND the description.

For each canonical prize (has description):
  1. Find matching project-derived prizes (no description) for same sponsor where
     canonical.title is a substring of the project-derived title
  2. Copy description (and amount) onto each matched project-derived prize
  3. Repoint any project_prizes from canonical → project-derived (safety check)
  4. Delete the canonical

Usage:
  python fix_ethonline2024_prize_dupes.py           # dry run
  python fix_ethonline2024_prize_dupes.py --apply   # write to Supabase
"""

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

EVENT_NAME = "ETHOnline 2024"


def main():
    apply = "--apply" in sys.argv

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    if not apply:
        print("DRY RUN — pass --apply to write changes\n")

    # Resolve event id
    event_result = supabase.table("events").select("id").eq("name", EVENT_NAME).execute()
    if not event_result.data:
        print(f"ERROR: '{EVENT_NAME}' not found in Supabase.")
        return
    event_id = event_result.data[0]["id"]
    print(f"{EVENT_NAME} event_id: {event_id}\n")

    # Fetch all prizes for this event
    prizes_result = supabase.table("prizes").select("id, title, description, amount, sponsor_id, prize_pool").eq("event_id", event_id).execute()
    prizes = prizes_result.data

    canonical  = [p for p in prizes if p.get("description")]
    no_desc    = [p for p in prizes if not p.get("description")]
    print(f"Prizes with description (canonical): {len(canonical)}")
    print(f"Prizes without description (project-derived): {len(no_desc)}\n")

    # Group no-description prizes by sponsor for fast lookup
    no_desc_by_sponsor: dict[int, list[dict]] = {}
    for p in no_desc:
        no_desc_by_sponsor.setdefault(p["sponsor_id"], []).append(p)

    merged = 0
    unmatched = 0

    for canon in canonical:
        sponsor_id = canon["sponsor_id"]
        canon_title = canon["title"].strip().lower()
        candidates = no_desc_by_sponsor.get(sponsor_id, [])

        # Find all project-derived prizes where canonical title is a substring
        matches = [
            p for p in candidates
            if canon_title in p["title"].strip().lower()
        ]

        if not matches:
            print(f"  UNMATCHED canonical: [{canon['id']}] {canon['title']!r}")
            unmatched += 1
            continue

        for proj in matches:
            print(
                f"  {'MERGING' if apply else 'WOULD MERGE'}:\n"
                f"    title:       {proj['title']!r} (kept)\n"
                f"    description: from canonical [{canon['id']}] {canon['title']!r}"
            )

            if apply:
                # Copy description + amount onto the project-derived prize
                supabase.table("prizes").update({
                    "description":    canon["description"],
                    "qualifications": canon.get("qualifications"),
                    "amount":         canon.get("amount"),
                }).eq("id", proj["id"]).execute()

                # Repoint any project_prizes pointing to canonical → project-derived
                supabase.table("project_prizes").update({"prize_id": proj["id"]}).eq("prize_id", canon["id"]).execute()

                # Delete the canonical
                supabase.table("prizes").delete().eq("id", canon["id"]).execute()

            merged += 1

        # After matching, remove matched prizes from candidates to avoid re-use
        no_desc_by_sponsor[sponsor_id] = [p for p in candidates if p not in matches]

    print(f"\n--- Summary ---")
    print(f"Merged: {merged}")
    print(f"Unmatched canonicals (kept as-is): {unmatched}")

    if not apply and merged:
        print("\nRe-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
