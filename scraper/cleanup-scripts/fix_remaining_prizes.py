"""
Fixes remaining malformed prize titles where "Prize Pool" was concatenated
onto the end and no clean counterpart exists to merge into.

For each malformed prize:
  - Strip "Prize Pool" suffix from title
  - Set prize_pool = True

Usage:
  python fix_remaining_prizes.py --test   # dry run
  python fix_remaining_prizes.py          # writes to Supabase
"""

import os
import re
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=".env")

DRY_RUN = "--test" in sys.argv

PRIZE_POOL_SUFFIX_RE = re.compile(r"\s*Prize\s*Pool\s*$", re.IGNORECASE)


def main():
    if DRY_RUN:
        print("DRY RUN — no writes\n")

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    all_prizes = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            supabase.table("prizes")
            .select("id, title")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        all_prizes.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    malformed = [
        p for p in all_prizes
        if PRIZE_POOL_SUFFIX_RE.search(p["title"]) and p["title"].strip().lower() != "prize pool"
    ]

    print(f"Total prizes: {len(all_prizes)}")
    print(f"Malformed to fix: {len(malformed)}\n")

    for p in malformed:
        clean_title = PRIZE_POOL_SUFFIX_RE.sub("", p["title"]).strip()
        print(f"[{p['id']}] {p['title']!r}  →  {clean_title!r}")
        if not DRY_RUN:
            supabase.table("prizes").update({
                "title": clean_title,
                "prize_pool": True,
            }).eq("id", p["id"]).execute()

    print(f"\nDone. {len(malformed)} prizes {'would be' if DRY_RUN else ''} fixed.")


if __name__ == "__main__":
    main()
