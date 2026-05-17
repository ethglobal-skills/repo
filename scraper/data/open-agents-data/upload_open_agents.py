"""
Uploads Open Agents projects and prizes from data/open-agents-data/projects_full.json.

For each project:
  1. Inserts the project row (event_id hardcoded to 77 for Open Agents)
  2. For each prize won:
     - Looks up or creates the sponsor by image_url
     - Looks up or creates the prize by (event_id, sponsor_id, title)
     - Creates the project_prizes join record

Usage:
  python upload_open_agents.py
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

INPUT_FILE = Path(__file__).parent / "data" / "open-agents-data" / "projects_full.json"
EVENT_ID = 77

ORDINAL_GLUE_RE = re.compile(r"(\w)(\d+(?:st|nd|rd|th))\s+place", re.IGNORECASE)
LEADING_NON_ASCII_RE = re.compile(r"^[^\x00-\x7F]+\s*")


def parse_prize_title(raw: str) -> tuple[str, str]:
    parts = re.split(r"\s*[-—]\s*", raw, maxsplit=1)
    if len(parts) == 2:
        sponsor_raw, title = parts[0].strip(), parts[1].strip()
    else:
        return raw.strip(), ""
    sponsor = LEADING_NON_ASCII_RE.sub("", sponsor_raw).strip()
    title = ORDINAL_GLUE_RE.sub(r"\1 \2 place", title)
    return sponsor, title


def get_or_create_sponsor(supabase, name: str, image_url: str, cache: dict) -> int:
    if image_url in cache:
        return cache[image_url]
    result = supabase.table("sponsors").select("id").eq("image_url", image_url).execute()
    if result.data:
        sid = result.data[0]["id"]
        cache[image_url] = sid
        return sid
    result = supabase.table("sponsors").insert({
        "name": name,
        "image_url": image_url or None,
    }).execute()
    sid = result.data[0]["id"]
    cache[image_url] = sid
    print(f"    + New sponsor: {name} (id={sid})")
    return sid


def get_or_create_prize(supabase, sponsor_id: int, title: str, prize_pool: bool, cache: dict) -> int:
    cache_key = (EVENT_ID, sponsor_id, title)
    if cache_key in cache:
        return cache[cache_key]
    result = (
        supabase.table("prizes")
        .select("id")
        .eq("event_id", EVENT_ID)
        .eq("sponsor_id", sponsor_id)
        .eq("title", title)
        .execute()
    )
    if result.data:
        pid = result.data[0]["id"]
        cache[cache_key] = pid
        return pid
    result = supabase.table("prizes").insert({
        "event_id":   EVENT_ID,
        "sponsor_id": sponsor_id,
        "title":      title,
        "prize_pool": prize_pool,
    }).execute()
    pid = result.data[0]["id"]
    cache[cache_key] = pid
    return pid


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    with open(INPUT_FILE) as f:
        data = json.load(f)

    projects = data["projects"]
    print(f"Uploading {len(projects)} Open Agents projects (event_id={EVENT_ID})...\n")

    sponsor_cache: dict[str, int] = {}
    prize_cache: dict[tuple, int] = {}

    for i, project in enumerate(projects, 1):
        print(f"[{i}/{len(projects)}] {project['title']}")

        try:
            result = supabase.table("projects").insert({
                "event_id":     EVENT_ID,
                "title":        project.get("title", ""),
                "url":          project.get("url") or None,
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

        for prize in project.get("prizes", []):
            prize_title_raw = prize.get("prize_title", "").strip()
            prize_image = prize.get("prize_image", "").strip()
            prize_pool = prize.get("prize_pool", False)

            if not prize_title_raw:
                continue

            sponsor_name, title = parse_prize_title(prize_title_raw)
            if not title:
                title = prize_title_raw

            sponsor_id = get_or_create_sponsor(supabase, sponsor_name, prize_image, sponsor_cache)
            prize_id = get_or_create_prize(supabase, sponsor_id, title, prize_pool, prize_cache)

            try:
                supabase.table("project_prizes").insert({
                    "project_id": project_id,
                    "prize_id":   prize_id,
                }).execute()
            except Exception:
                pass  # unique constraint — already linked

    print(f"\nDone. {len(projects)} projects uploaded.")


if __name__ == "__main__":
    main()
