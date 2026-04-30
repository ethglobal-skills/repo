"""
Scrapes past hackathon and online events from https://ethglobal.com/events.
Output: data/events.json

Each entry:
  { "name", "url", "logo_url", "city", "country", "start_date", "end_date" }
"""

import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ethglobal.com"
OUTPUT_FILE = Path(__file__).parent / "data" / "events.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")
KEEP_TAGS = {"hackathon", "online"}


def parse_date(raw: str) -> str:
    raw = ORDINAL_RE.sub(r"\1", raw).strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def get_tag(a) -> str:
    """Find the tag badge by exact text match to avoid hitting description text."""
    for s in a.find_all(string=True):
        t = s.strip().lower()
        if t in KEEP_TAGS:
            return s.strip()
    return ""


def scrape_events() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    response = session.get(f"{BASE_URL}/events", timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    past_heading = soup.find(
        lambda tag: tag.name in ["h2", "h3"] and "Past" in tag.get_text()
    )
    if not past_heading:
        print("'Past' heading not found")
        return []

    # Grab ALL <a> tags after Past heading — old events use external URLs
    all_links = past_heading.find_all_next("a", href=True)
    print(f"Total <a> tags after Past: {len(all_links)}")

    # Filter to event cards: must have an img and an h2/h3 child
    event_cards = [
        a for a in all_links
        if a.find("img") and a.find(["h2", "h3"])
    ]
    print(f"Event cards (has img + heading): {len(event_cards)}\n")

    events = []
    for a in event_cards:
        tag = get_tag(a)
        if tag.lower() not in KEEP_TAGS:
            continue

        href = a.get("href", "")
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        name_el = a.find(["h2", "h3"])
        name = name_el.get_text(strip=True) if name_el else ""

        img = a.find("img")
        logo_url = img.get("src", "") if img else ""

        time_els = a.find_all("time")
        start_date = end_date = ""
        if len(time_els) >= 2:
            start_date = parse_date(time_els[0].get_text(strip=True))
            end_date = parse_date(time_els[-1].get_text(strip=True))
            if not start_date and end_date:
                year = end_date[:4]
                raw = ORDINAL_RE.sub(r"\1", time_els[0].get_text(strip=True)).strip()
                start_date = parse_date(f"{raw}, {year}")
        elif len(time_els) == 1:
            start_date = end_date = parse_date(time_els[0].get_text(strip=True))

        # Location: short text nodes that aren't the name, tag, or dates
        skip = {name, tag, tag.upper(), start_date, end_date}
        candidates = []
        seen = set()
        for el in a.find_all(["div", "p", "span"]):
            t = el.get_text(strip=True)
            if (t and t not in skip and t not in seen
                    and len(t) < 50 and not re.search(r"\d", t)
                    and t.lower() not in KEEP_TAGS):
                seen.add(t)
                candidates.append(t)

        city = candidates[0] if candidates else ""
        country = candidates[1] if len(candidates) > 1 else ""

        print(f"  {name[:45]:<45} | {tag:<10} | {start_date} → {end_date}")
        events.append({
            "name": name,
            "url": url,
            "logo_url": logo_url,
            "city": city,
            "country": country,
            "start_date": start_date,
            "end_date": end_date,
        })

    return events


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    events = scrape_events()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, indent=2, ensure_ascii=False)
    print(f"\nDone. {len(events)} events saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
