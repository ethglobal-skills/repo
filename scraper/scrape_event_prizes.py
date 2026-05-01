"""
Scrapes /events/{slug}/prizes pages for sponsor bounty details.
For each prize found on the page:
  - Matches to existing prize records in DB (event + sponsor + fuzzy title)
  - Updates description and qualifications
  - Creates prize records for upcoming events (not yet in DB)
  - Creates sponsor_docs entries for Links and Resources

Covers Istanbul (Nov 2023) through present/upcoming events.

Usage:
  python scrape_event_prizes.py --test   # dry run, prints what it would do
  python scrape_event_prizes.py          # writes to Supabase
"""

import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = "--test" in sys.argv

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

LEADING_EMOJI_RE = re.compile(r"^[^\x00-\x7F]+\s*")
ORDINAL_PLACE_RE = re.compile(r"\s*\d+(?:st|nd|rd|th)\s+place\s*$", re.IGNORECASE)


def strip_emoji(text: str) -> str:
    return LEADING_EMOJI_RE.sub("", text).strip()


def normalize_title(title: str) -> str:
    """Remove trailing ordinal place suffix for fuzzy matching."""
    return ORDINAL_PLACE_RE.sub("", title).strip().lower()


def get_text_after(heading) -> str:
    """Collect text from siblings after a heading until the next heading."""
    parts = []
    for sibling in heading.next_siblings:
        if sibling.name in ["h2", "h3", "h4"]:
            break
        if hasattr(sibling, "get_text"):
            t = sibling.get_text(separator="\n", strip=True)
            if t:
                parts.append(t)
    return "\n".join(parts).strip()


def scrape_sponsor_section(container) -> dict:
    """Extract all data from one sponsor's container div."""
    # Logo URL (left column image)
    img = container.find("img", src=lambda s: s and "organizations" in s)
    logo_url = img.get("src", "") if img else ""

    # About text
    about_h3 = container.find("h3", string=lambda t: t and t.strip() == "About")
    about = ""
    if about_h3:
        about_div = about_h3.find_next_sibling("div")
        about = about_div.get_text(separator="\n", strip=True) if about_div else ""

    # Prize blocks
    prizes = []
    prizes_h3 = container.find("h3", string=lambda t: t and t.strip() == "Prizes")
    if prizes_h3:
        prize_blocks = prizes_h3.parent.find_all("div", attrs={"id": "collapsible-data"})
        for block in prize_blocks:
            # Title
            title_span = block.find("span", class_="text-xl font-semibold break-normal")
            if not title_span:
                continue
            title = strip_emoji(title_span.get_text(strip=True))
            if not title:
                continue

            # Description (div with mt-1.5 class)
            desc_div = block.find(
                "div",
                class_=lambda c: c and "mt-1.5" in c and "mb-2" in c and "text-lg" in c,
            )
            description = desc_div.get_text(separator="\n", strip=True) if desc_div else ""

            # Qualification Requirements
            qual_h3 = block.find(
                "h3",
                string=lambda t: t and "Qualification" in t,
            )
            qualifications = get_text_after(qual_h3) if qual_h3 else ""

            # Links and Resources
            links = []
            links_h3 = block.find(
                "h3",
                string=lambda t: t and "Links" in t and "Resources" in t,
            )
            if links_h3:
                for sibling in links_h3.next_siblings:
                    if hasattr(sibling, "name") and sibling.name in ["h2", "h3"]:
                        break
                    if hasattr(sibling, "find_all"):
                        for a in sibling.find_all("a", href=True):
                            href = a.get("href", "")
                            if not href or href.startswith("#"):
                                continue
                            # Strip embedded URL text and ↗ arrow from the display name
                            full_text = a.get_text(strip=True)
                            name = re.sub(r"https?://\S+|↗", "", full_text).strip()
                            if name:
                                links.append({"name": name, "url": href})

            prizes.append({
                "title": title,
                "description": description,
                "qualifications": qualifications,
                "links": links,
            })

    return {"logo_url": logo_url, "about": about, "prizes": prizes}


def scrape_prizes_page(url: str) -> list[dict]:
    """Fetch a prizes page and return list of sponsor data dicts."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    sponsors = []
    # Each sponsor section is a div with these classes
    containers = soup.find_all(
        "div",
        class_=lambda c: c and "border-b-2" in c and "border-b-gray-200" in c and "mb-12" in c,
    )
    for container in containers:
        h2 = container.find("h2")
        if not h2:
            continue
        name = h2.get_text(strip=True)
        if "finalist" in name.lower():
            continue
        data = scrape_sponsor_section(container)
        data["name"] = name
        sponsors.append(data)

    return sponsors


def process_event(supabase, event: dict, http_session: requests.Session):
    event_id = event["id"]
    event_name = event["name"]
    event_url = event.get("url", "")

    # Derive prizes page URL from event URL
    slug = event_url.rstrip("/").split("/events/")[-1]
    prizes_url = f"https://ethglobal.com/events/{slug}/prizes"

    print(f"\n{'='*60}")
    print(f"Event: {event_name} (id={event_id})")
    print(f"URL: {prizes_url}")

    try:
        sponsors = scrape_prizes_page(prizes_url)
    except Exception as e:
        print(f"  ! Failed to fetch: {e}")
        return

    print(f"  Sponsors found: {len(sponsors)}")

    # Preload existing prizes for this event
    existing_prizes = (
        supabase.table("prizes")
        .select("id, title, sponsor_id")
        .eq("event_id", event_id)
        .execute()
        .data
        if not DRY_RUN else []
    )
    # Build lookup: normalized_title → [prize_id, ...]
    prize_lookup: dict[str, list[int]] = {}
    for p in existing_prizes:
        key = normalize_title(p["title"])
        prize_lookup.setdefault(key, []).append(p["id"])

    for sponsor_data in sponsors:
        sponsor_name = sponsor_data["name"]
        logo_url = sponsor_data["logo_url"]
        about = sponsor_data["about"]
        prizes = sponsor_data["prizes"]

        print(f"\n  Sponsor: {sponsor_name} | logo: {logo_url}")

        # Get or create sponsor
        sponsor_id = None
        if not DRY_RUN:
            result = supabase.table("sponsors").select("id").eq("image_url", logo_url).execute()
            if result.data:
                sponsor_id = result.data[0]["id"]
                # Update about if missing
                if about:
                    supabase.table("sponsors").update({"about": about}).eq("id", sponsor_id).execute()
            else:
                result = supabase.table("sponsors").insert({
                    "name": sponsor_name,
                    "image_url": logo_url or None,
                    "about": about or None,
                }).execute()
                sponsor_id = result.data[0]["id"]
                print(f"    + Created sponsor id={sponsor_id}")
        else:
            print(f"    [DRY RUN] Would upsert sponsor: {sponsor_name}")

        for prize in prizes:
            title = prize["title"]
            description = prize["description"]
            qualifications = prize["qualifications"]
            links = prize["links"]

            print(f"    Prize: {title}")
            if description:
                print(f"      desc: {description[:80]}...")
            if qualifications:
                print(f"      qual: {qualifications[:80]}...")
            for link in links:
                print(f"      link: {link['name']} → {link['url']}")

            if DRY_RUN:
                continue

            norm = title.lower()
            matched_ids = prize_lookup.get(norm, [])

            if matched_ids:
                # Update existing prizes (all place variants)
                for prize_id in matched_ids:
                    supabase.table("prizes").update({
                        "description": description or None,
                        "qualifications": qualifications or None,
                    }).eq("id", prize_id).execute()
                print(f"      → Updated {len(matched_ids)} prize record(s)")
            else:
                # Create new prize (upcoming event or unmatched)
                result = supabase.table("prizes").insert({
                    "event_id": event_id,
                    "sponsor_id": sponsor_id,
                    "title": title,
                    "description": description or None,
                    "qualifications": qualifications or None,
                }).execute()
                new_id = result.data[0]["id"]
                print(f"      + Created new prize id={new_id}")

            # Upsert sponsor_docs
            for link in links:
                if not DRY_RUN:
                    existing = (
                        supabase.table("sponsor_docs")
                        .select("id")
                        .eq("sponsor_id", sponsor_id)
                        .eq("event_id", event_id)
                        .eq("url", link["url"])
                        .execute()
                    )
                    if not existing.data:
                        supabase.table("sponsor_docs").insert({
                            "sponsor_id": sponsor_id,
                            "event_id": event_id,
                            "name": link["name"],
                            "url": link["url"],
                        }).execute()


def main():
    if DRY_RUN:
        print("DRY RUN — no writes to Supabase\n")

    from supabase import create_client
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    http_session = requests.Session()
    http_session.headers.update(HEADERS)

    # All ethglobal.com/events/ entries from Istanbul (Nov 2023) onwards
    # Istanbul event id is known; we filter by URL pattern and date
    all_events = (
        supabase.table("events")
        .select("id, name, url, start_date")
        .like("url", "https://ethglobal.com/events/%")
        .gte("start_date", "2023-11-01")
        .lte("start_date", "2026-05-06")
        .order("start_date", desc=False)
        .execute()
        .data
    )

    print(f"Events to process: {len(all_events)}")
    for event in all_events:
        print(f"  [{event['id']}] {event['name']} ({event['start_date']})")

    print()
    for event in all_events:
        process_event(supabase, event, http_session)
        time.sleep(2)

    print("\n\nDone.")


if __name__ == "__main__":
    main()
