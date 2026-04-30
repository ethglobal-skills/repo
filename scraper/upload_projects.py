"""
Uploads projects and their prizes from data/projects_full.json to Supabase.
For each project prize:
  1. Parses sponsor name + prize title from the prize_title string
  2. Looks up or creates a sponsor record using prize_image as the unique key
  3. Looks up or creates a prize record (event + sponsor + title)
  4. Creates a project_prizes join record

Run upload_events.py first so event IDs exist.

Usage:
  python upload_projects.py
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

INPUT_FILE = Path(__file__).parent / "data" / "projects_full.json"

# Regex: insert space before ordinals glued to a word ("Potential1st" → "Potential 1st")
ORDINAL_GLUE_RE = re.compile(r"(\w)(\d+(?:st|nd|rd|th))\s+place", re.IGNORECASE)
# Leading emoji / non-ASCII stripper for sponsor names
LEADING_NON_ASCII_RE = re.compile(r"^[^\x00-\x7F]+\s*")


def parse_prize_title(raw: str) -> tuple[str, str]:
    """Split 'Sponsor - Prize Title' on first - or —, return (sponsor, title)."""
    parts = re.split(r"\s*[-—]\s*", raw, maxsplit=1)
    if len(parts) == 2:
        sponsor_raw, title = parts[0].strip(), parts[1].strip()
    else:
        return raw.strip(), ""

    # Strip leading emoji from sponsor name
    sponsor = LEADING_NON_ASCII_RE.sub("", sponsor_raw).strip()

    # Insert space before glued ordinals in title ("Potential1st place" → "Potential 1st place")
    title = ORDINAL_GLUE_RE.sub(r"\1 \2 place", title)

    return sponsor, title


def normalize_event_name(name: str) -> str:
    """Lowercase, strip years and extra whitespace for fuzzy matching."""
    name = re.sub(r"\b20\d{2}\b", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def build_event_lookup(supabase) -> dict[str, int]:
    """Returns {normalized_name: event_id} for all events in DB."""
    result = supabase.table("events").select("id, name").execute()
    lookup = {}
    for row in result.data:
        key = normalize_event_name(row["name"])
        lookup[key] = row["id"]
    return lookup


def resolve_event_id(event_name: str, lookup: dict[str, int]) -> int | None:
    normalized = normalize_event_name(event_name)
    # Exact match first
    if normalized in lookup:
        return lookup[normalized]
    # Substring match
    for key, event_id in lookup.items():
        if key in normalized or normalized in key:
            return event_id
    return None


def get_or_create_sponsor(supabase, name: str, image_url: str, sponsor_cache: dict) -> int:
    """Look up sponsor by image_url; create if not found. Returns sponsor id."""
    if image_url in sponsor_cache:
        return sponsor_cache[image_url]

    # Check DB
    result = supabase.table("sponsors").select("id").eq("image_url", image_url).execute()
    if result.data:
        sponsor_id = result.data[0]["id"]
        sponsor_cache[image_url] = sponsor_id
        return sponsor_id

    # Create new sponsor
    result = supabase.table("sponsors").insert({
        "name": name,
        "image_url": image_url or None,
    }).execute()
    sponsor_id = result.data[0]["id"]
    sponsor_cache[image_url] = sponsor_id
    print(f"    + New sponsor: {name} (id={sponsor_id})")
    return sponsor_id


def get_or_create_prize(supabase, event_id: int, sponsor_id: int, title: str,
                        prize_pool: bool, prize_cache: dict) -> int:
    """Look up prize by (event_id, sponsor_id, title); create if not found."""
    cache_key = (event_id, sponsor_id, title)
    if cache_key in prize_cache:
        return prize_cache[cache_key]

    result = (
        supabase.table("prizes")
        .select("id")
        .eq("event_id", event_id)
        .eq("sponsor_id", sponsor_id)
        .eq("title", title)
        .execute()
    )
    if result.data:
        prize_id = result.data[0]["id"]
        prize_cache[cache_key] = prize_id
        return prize_id

    result = supabase.table("prizes").insert({
        "event_id":   event_id,
        "sponsor_id": sponsor_id,
        "title":      title,
        "prize_pool": prize_pool,
        # description and amount filled later from event prizes page scrape
    }).execute()
    prize_id = result.data[0]["id"]
    prize_cache[cache_key] = prize_id
    return prize_id


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    with open(INPUT_FILE) as f:
        data = json.load(f)

    projects = data["projects"]
    print(f"Uploading {len(projects)} projects...\n")

    event_lookup = build_event_lookup(supabase)
    sponsor_cache: dict[str, int] = {}  # image_url → sponsor_id
    prize_cache: dict[tuple, int] = {}  # (event_id, sponsor_id, title) → prize_id
    skipped_events = set()

    for i, project in enumerate(projects, 1):
        print(f"[{i}/{len(projects)}] {project['title']}")

        # Resolve event
        event_name = project.get("event", "")
        event_id = resolve_event_id(event_name, event_lookup)
        if not event_id:
            if event_name not in skipped_events:
                print(f"  ! Could not match event: '{event_name}' — skipping prizes")
                skipped_events.add(event_name)

        # Insert project
        try:
            result = supabase.table("projects").insert({
                "event_id":     event_id,
                "title":        project.get("title", ""),
                "url":          project.get("url", "") or None,
                "tagline":      project.get("tagline") or None,
                "description":  project.get("description") or None,
                "how_its_made": project.get("how_its_made") or None,
                "github":       project.get("github") or None,
                "live_demo":    project.get("live_demo") or None,
            }).execute()
        except Exception as e:
            print(f"  ! Insert failed: {e}")
            continue

        project_id = result.data[0]["id"]

        # Process prizes
        for prize in project.get("prizes", []):
            prize_title_raw = prize.get("prize_title", "").strip()
            prize_image = prize.get("prize_image", "").strip()
            prize_pool = prize.get("prize_pool", False)

            if not prize_title_raw:
                continue

            sponsor_name, title = parse_prize_title(prize_title_raw)
            if not title:
                title = prize_title_raw  # fallback: use full string as title

            sponsor_id = get_or_create_sponsor(supabase, sponsor_name, prize_image, sponsor_cache)

            if event_id:
                prize_id = get_or_create_prize(
                    supabase, event_id, sponsor_id, title, prize_pool, prize_cache
                )
                try:
                    supabase.table("project_prizes").insert({
                        "project_id": project_id,
                        "prize_id":   prize_id,
                    }).execute()
                except Exception:
                    pass  # unique constraint — already linked

    print(f"\nDone. {len(projects)} projects uploaded.")
    if skipped_events:
        print(f"Events with no match ({len(skipped_events)}):")
        for e in sorted(skipped_events):
            print(f"  - {e}")


if __name__ == "__main__":
    main()
