"""
Fixes prizes incorrectly assigned to the wrong event due to fuzzy year-stripping
during upload. Uses project_prizes → projects.event_id as source of truth (projects
must already be corrected before running this).

For each bloated event's prizes:
  1. Find all projects associated via project_prizes
  2. If all projects belong to a different event → repoint the prize
  3. If projects span multiple events → duplicate the prize per event, repoint each group

Usage:
  python fix_prize_events.py           # dry run
  python fix_prize_events.py --apply   # write to Supabase
"""

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Events whose prizes got incorrectly collapsed into them.
# Add or remove as needed.
BLOATED_EVENTS = [
    "ETHOnline 2025",
    "Scaling Ethereum 2024",
    "ETHGlobal New York 2025",
    "ETHIndia 2023",
]


def fix_event(supabase, bloated_event_name: str, event_name_to_id: dict, event_id_to_name: dict, apply: bool):
    bloated_event_id = event_name_to_id.get(bloated_event_name)
    if not bloated_event_id:
        print(f"  ERROR: '{bloated_event_name}' not found in Supabase — skipping\n")
        return

    prizes_result = supabase.table("prizes").select("id, title, sponsor_id, prize_pool").eq("event_id", bloated_event_id).execute()
    prizes = prizes_result.data
    print(f"  Prizes under '{bloated_event_name}': {len(prizes)}")

    corrections = 0
    conflict_list = []
    no_project_list = []

    for prize in prizes:
        prize_id = prize["id"]

        pp_result = supabase.table("project_prizes").select("project_id").eq("prize_id", prize_id).execute()
        project_ids = [row["project_id"] for row in pp_result.data]

        if not project_ids:
            no_project_list.append(prize)
            continue

        projects_result = supabase.table("projects").select("id, event_id").in_("id", project_ids).execute()
        event_id_counts = Counter(row["event_id"] for row in projects_result.data if row["event_id"])

        if not event_id_counts:
            no_project_list.append(prize)
            continue

        if len(event_id_counts) > 1:
            conflict_list.append((prize, event_id_counts, projects_result.data))
            continue

        correct_event_id = next(iter(event_id_counts))
        if correct_event_id == bloated_event_id:
            continue

        correct_event_name = event_id_to_name.get(correct_event_id, str(correct_event_id))
        print(f"    {'UPDATING' if apply else 'WOULD UPDATE'} prize_id={prize_id} {prize['title']!r} → {correct_event_name!r}")

        if apply:
            supabase.table("prizes").update({"event_id": correct_event_id}).eq("id", prize_id).execute()

        corrections += 1

    # Handle conflicts — split prize into one record per event
    if conflict_list:
        print(f"\n  Conflicts ({len(conflict_list)}) — splitting prizes by event:")
    for prize, event_id_counts, project_rows in conflict_list:
        breakdown = {event_id_to_name.get(eid, str(eid)): count for eid, count in event_id_counts.items()}
        print(f"    prize_id={prize['id']} {prize['title']!r}: {breakdown}")

        projects_by_event: dict[int, list[int]] = {}
        for row in project_rows:
            eid = row["event_id"]
            if eid:
                projects_by_event.setdefault(eid, []).append(row["id"])

        event_ids = list(projects_by_event.keys())
        anchor_event_id = bloated_event_id if bloated_event_id in event_ids else event_ids[0]
        other_event_ids = [eid for eid in event_ids if eid != anchor_event_id]

        if anchor_event_id != bloated_event_id:
            anchor_name = event_id_to_name.get(anchor_event_id, str(anchor_event_id))
            print(f"      {'UPDATING' if apply else 'WOULD UPDATE'} original prize → {anchor_name!r}")
            if apply:
                supabase.table("prizes").update({"event_id": anchor_event_id}).eq("id", prize["id"]).execute()

        for eid in other_event_ids:
            event_name = event_id_to_name.get(eid, str(eid))
            pids = projects_by_event[eid]
            print(f"      {'CREATING' if apply else 'WOULD CREATE'} duplicate for {event_name!r} → repoint {len(pids)} project(s)")

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

    print(f"\n  Summary: {corrections} corrected, {len(conflict_list)} split, {len(no_project_list)} with no projects")

    if no_project_list:
        print(f"  No associated projects:")
        for prize in no_project_list:
            print(f"    prize_id={prize['id']} {prize['title']!r}")

    print()


def main():
    apply = "--apply" in sys.argv

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    if not apply:
        print("DRY RUN — pass --apply to write changes\n")

    events_result = supabase.table("events").select("id, name").execute()
    event_name_to_id = {row["name"]: row["id"] for row in events_result.data}
    event_id_to_name = {v: k for k, v in event_name_to_id.items()}

    for event_name in BLOATED_EVENTS:
        print(f"=== {event_name} ===")
        fix_event(supabase, event_name, event_name_to_id, event_id_to_name, apply)

    if not apply:
        print("Re-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
