"""
Merges duplicate prizes for Open Agents (event_id=77).

  - Canonical (from event page): clean title, has description, no placement
  - Project-derived (from project pages): title with placement (1st/2nd/3rd), no description

Goal: end up with one prize per placement that has BOTH the placement title AND the description.

For each canonical prize (has description):
  1. Find matching project-derived prizes where canonical.title is a substring of the project title
  2. Copy description onto each matched project-derived prize
  3. Repoint any project_prizes from canonical → project-derived (safety)
  4. Delete the canonical

Then delete any remaining canonical prizes with no project_prizes linked.

Usage:
  python fix_open_agents_prize_dupes.py           # dry run
  python fix_open_agents_prize_dupes.py --apply   # write to Supabase
"""

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

EVENT_ID = 77


def main():
    apply = "--apply" in sys.argv

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    if not apply:
        print("DRY RUN — pass --apply to write changes\n")

    prizes = supabase.table("prizes").select("id, title, description, amount, sponsor_id, prize_pool").eq("event_id", EVENT_ID).execute().data

    canonical = [p for p in prizes if p.get("description")]
    no_desc   = [p for p in prizes if not p.get("description")]
    print(f"Canonical (with description): {len(canonical)}")
    print(f"Project-derived (no description): {len(no_desc)}\n")

    # Group project-derived by sponsor for lookup
    no_desc_by_sponsor: dict[int, list[dict]] = {}
    for p in no_desc:
        no_desc_by_sponsor.setdefault(p["sponsor_id"], []).append(p)

    merged = 0
    unmatched_canonicals = []

    for canon in canonical:
        sponsor_id  = canon["sponsor_id"]
        canon_title = canon["title"].strip().lower()
        candidates  = no_desc_by_sponsor.get(sponsor_id, [])

        matches = [p for p in candidates if canon_title in p["title"].strip().lower()]

        if not matches:
            unmatched_canonicals.append(canon)
            continue

        for proj in matches:
            print(
                f"  {'MERGING' if apply else 'WOULD MERGE'}:\n"
                f"    keep:  [{proj['id']}] {proj['title']!r}\n"
                f"    desc:  from [{canon['id']}] {canon['title']!r}"
            )
            if apply:
                supabase.table("prizes").update({
                    "description":    canon["description"],
                    "qualifications": canon.get("qualifications"),
                    "amount":         canon.get("amount"),
                }).eq("id", proj["id"]).execute()

                # Repoint any project_prizes from canonical → project-derived
                supabase.table("project_prizes").update({"prize_id": proj["id"]}).eq("prize_id", canon["id"]).execute()

                supabase.table("prizes").delete().eq("id", canon["id"]).execute()

            merged += 1

        # Remove matched from candidates pool
        no_desc_by_sponsor[sponsor_id] = [p for p in candidates if p not in matches]

    # Delete unmatched canonicals that have no project_prizes
    print(f"\nChecking {len(unmatched_canonicals)} unmatched canonical(s) for project links...")
    deleted = 0
    kept = 0
    for canon in unmatched_canonicals:
        pp = supabase.table("project_prizes").select("project_id").eq("prize_id", canon["id"]).execute()
        if pp.data:
            print(f"  KEEPING [{canon['id']}] {canon['title']!r} — has {len(pp.data)} project link(s)")
            kept += 1
        else:
            print(f"  {'DELETING' if apply else 'WOULD DELETE'} [{canon['id']}] {canon['title']!r} — no projects linked")
            if apply:
                supabase.table("prizes").delete().eq("id", canon["id"]).execute()
            deleted += 1

    print(f"\n--- Summary ---")
    print(f"Merged:   {merged}")
    print(f"Deleted (no projects): {deleted}")
    print(f"Kept (had project links): {kept}")

    if not apply and (merged or deleted):
        print("\nRe-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
