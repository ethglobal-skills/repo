"""
Cleans up malformed prize titles where "Prize Pool" was incorrectly
concatenated onto the end (e.g. "World Pool PrizePrize Pool").

For each malformed prize:
  1. Strip "Prize Pool" from the end to get the clean title
  2. Find the correct prize with the clean title (same event + sponsor)
  3. Move any project_prizes references to the correct prize
  4. Delete the malformed prize

Usage:
  python cleanup_prizes.py --test   # dry run
  python cleanup_prizes.py          # writes to Supabase
"""

import os
import re
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DRY_RUN = "--test" in sys.argv

PRIZE_POOL_SUFFIX_RE = re.compile(r"\s*Prize\s*Pool\s*$", re.IGNORECASE)


def main():
    if DRY_RUN:
        print("DRY RUN — no writes\n")

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    # Fetch all prizes (paginate to avoid 1000 row default limit)
    all_prizes = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            supabase.table("prizes")
            .select("id, event_id, sponsor_id, title, prize_pool")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        all_prizes.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    print(f"Total prizes: {len(all_prizes)}")

    # Find malformed ones: title ends with "Prize Pool" but title != "Prize Pool"
    malformed = [
        p for p in all_prizes
        if PRIZE_POOL_SUFFIX_RE.search(p["title"]) and p["title"].strip().lower() != "prize pool"
    ]
    print(f"Malformed prizes found: {len(malformed)}\n")

    # Build lookup: (event_id, sponsor_id, clean_title_lower) → prize
    prize_lookup = {
        (p["event_id"], p["sponsor_id"], p["title"].strip().lower()): p
        for p in all_prizes
    }

    fixed = 0
    for bad in malformed:
        clean_title = PRIZE_POOL_SUFFIX_RE.sub("", bad["title"]).strip()
        key = (bad["event_id"], bad["sponsor_id"], clean_title.lower())
        correct = prize_lookup.get(key)

        print(f"Bad:     [{bad['id']}] {bad['title']!r}")
        print(f"Clean:   {clean_title!r}")

        if correct:
            print(f"Correct: [{correct['id']}] {correct['title']!r}")
            if not DRY_RUN:
                # Move project_prizes references to the correct prize
                supabase.table("project_prizes").update(
                    {"prize_id": correct["id"]}
                ).eq("prize_id", bad["id"]).execute()
                # Delete the malformed prize
                supabase.table("prizes").delete().eq("id", bad["id"]).execute()
                print(f"  → Merged into [{correct['id']}] and deleted bad record")
            else:
                print(f"  [DRY RUN] Would merge into [{correct['id']}] and delete [{bad['id']}]")
        else:
            candidates = [
                p for p in all_prizes
                if p["event_id"] == bad["event_id"] and p["sponsor_id"] == bad["sponsor_id"]
            ]
            print(f"  event_id={bad['event_id']} sponsor_id={bad['sponsor_id']}")
            print(f"  Prizes for same event+sponsor: {[p['title'] for p in candidates]}")
            print(f"  No matching correct prize found — skipping")

        print()
        fixed += 1

    print(f"Done. {fixed} malformed prizes {'would be' if DRY_RUN else ''} fixed.")


if __name__ == "__main__":
    main()
