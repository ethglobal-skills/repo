"""
Fixes prizes incorrectly assigned to HackFS 2024 that belong to HackFS 2021/2022/2023.

The upload script's fuzzy year-stripping caused all HackFS prize event_ids to
collapse to HackFS 2024. Since project event_ids are already corrected, we use:
  project_prizes → projects.event_id  as the source of truth.

For each HackFS 2024 prize:
  1. Find all projects associated with it via project_prizes
  2. If all associated projects belong to a different HackFS event, repoint the prize
  3. If projects span multiple events, flag for manual review

Usage:
  python fix_hackfs_prizes.py           # dry run
  python fix_hackfs_prizes.py --apply   # write to Supabase
"""

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def main():
    apply = "--apply" in sys.argv

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    if not apply:
        print("DRY RUN — pass --apply to write changes\n")

    # Build event name → id lookup
    events_result = supabase.table("events").select("id, name").execute()
    event_name_to_id = {row["name"]: row["id"] for row in events_result.data}
    event_id_to_name = {v: k for k, v in event_name_to_id.items()}

    hackfs_events = {name: eid for name, eid in event_name_to_id.items() if "hackfs" in name.lower()}
    print(f"HackFS events in Supabase: {hackfs_events}\n")

    hackfs_2024_id = event_name_to_id.get("HackFS 2024")
    if not hackfs_2024_id:
        print("ERROR: Could not find HackFS 2024 event in Supabase.")
        return

    # Fetch all prizes currently assigned to HackFS 2024
    prizes_result = supabase.table("prizes").select("id, title, sponsor_id").eq("event_id", hackfs_2024_id).execute()
    prizes = prizes_result.data
    print(f"Prizes under HackFS 2024: {len(prizes)}\n")

    corrections = 0
    conflict_list = []
    no_project_list = []

    for prize in prizes:
        prize_id = prize["id"]

        # Find all projects associated with this prize
        pp_result = (
            supabase.table("project_prizes")
            .select("project_id")
            .eq("prize_id", prize_id)
            .execute()
        )
        project_ids = [row["project_id"] for row in pp_result.data]

        if not project_ids:
            no_project_list.append(prize)
            continue

        # Look up those projects' event_ids
        projects_result = (
            supabase.table("projects")
            .select("id, event_id")
            .in_("id", project_ids)
            .execute()
        )
        event_id_counts = Counter(row["event_id"] for row in projects_result.data if row["event_id"])

        if not event_id_counts:
            no_project_list.append(prize)
            continue

        if len(event_id_counts) > 1:
            conflict_list.append((prize, event_id_counts, projects_result.data))
            continue

        correct_event_id = next(iter(event_id_counts))

        if correct_event_id == hackfs_2024_id:
            continue

        correct_event_name = event_id_to_name.get(correct_event_id, str(correct_event_id))
        print(
            f"  {'UPDATING' if apply else 'WOULD UPDATE'} prize_id={prize_id} {prize['title']!r}\n"
            f"    HackFS 2024 → {correct_event_name!r}"
        )

        if apply:
            supabase.table("prizes").update({"event_id": correct_event_id}).eq("id", prize_id).execute()

        corrections += 1

    print(f"\n--- Summary ---")
    print(f"Corrections: {corrections}")

    print(f"\nConflicts ({len(conflict_list)}) — splitting prizes by event:")
    for prize, event_id_counts, project_rows in conflict_list:
        breakdown = {event_id_to_name.get(eid, str(eid)): count for eid, count in event_id_counts.items()}
        print(f"  prize_id={prize['id']} {prize['title']!r}: {breakdown}")

        # Group project_ids by event_id
        projects_by_event: dict[int, list[int]] = {}
        for row in project_rows:
            eid = row["event_id"]
            if eid:
                projects_by_event.setdefault(eid, []).append(row["id"])

        # Keep the original prize for HackFS 2024 if present, otherwise the first group
        event_ids = list(projects_by_event.keys())
        anchor_event_id = hackfs_2024_id if hackfs_2024_id in event_ids else event_ids[0]
        other_event_ids = [eid for eid in event_ids if eid != anchor_event_id]

        # Update original prize's event_id to anchor if it isn't already
        if anchor_event_id != hackfs_2024_id:
            anchor_name = event_id_to_name.get(anchor_event_id, str(anchor_event_id))
            print(f"    {'UPDATING' if apply else 'WOULD UPDATE'} original prize → {anchor_name!r}")
            if apply:
                supabase.table("prizes").update({"event_id": anchor_event_id}).eq("id", prize["id"]).execute()

        # For each remaining event, create a duplicate prize and repoint project_prizes
        for eid in other_event_ids:
            event_name = event_id_to_name.get(eid, str(eid))
            pids = projects_by_event[eid]
            print(f"    {'CREATING' if apply else 'WOULD CREATE'} duplicate prize for {event_name!r} → repoint {len(pids)} project(s)")

            if apply:
                new_prize = supabase.table("prizes").insert({
                    "event_id":   eid,
                    "sponsor_id": prize["sponsor_id"],
                    "title":      prize["title"],
                    "prize_pool": prize.get("prize_pool", False),
                }).execute()
                new_prize_id = new_prize.data[0]["id"]

                for pid in pids:
                    supabase.table("project_prizes").update({"prize_id": new_prize_id}).eq("project_id", pid).eq("prize_id", prize["id"]).execute()

    print(f"\nNo associated projects ({len(no_project_list)}):")
    for prize in no_project_list:
        print(f"  prize_id={prize['id']} {prize['title']!r}")

    if corrections and not apply:
        print("\nRe-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
