"""
Scrapes Open Agents projects from https://ethglobal.com/showcase.
Stops as soon as a project's event is no longer "Open Agents".
Output: data/open-agents-data/projects_raw.json

Usage:
  python scrape_open_agents.py
  python scrape_open_agents.py --test   # scrape first page only
"""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ethglobal.com"
OUTPUT_FILE = Path(__file__).parent / "data" / "open-agents-data" / "projects_raw.json"
TARGET_EVENT = "Open Agents"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_open_agents(test_mode: bool = False) -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    projects: list[dict] = []
    page_num = 1

    while True:
        print(f"\n=== Page {page_num} ===")
        url = f"{BASE_URL}/showcase?page={page_num}"
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            print(f"  Got status {response.status_code}, stopping.")
            break

        soup = BeautifulSoup(response.text, "lxml")
        all_links = soup.find_all("a")

        count = 0
        done = False
        position = 0

        for link in all_links:
            href = link.get("href", "")
            if not href.startswith("/showcase/"):
                continue

            if position == 32:
                position += 1
                continue

            h2 = link.find("h2")
            title = h2.text.strip() if h2 else None

            div = link.find("div")
            event = div.text.strip() if div else None

            if event != TARGET_EVENT:
                print(f"  Hit non-Open Agents event: {event!r} — stopping.")
                done = True
                break

            if title:
                project_url = f"{BASE_URL}{href}"
                projects.append({
                    "title": title,
                    "event": event,
                    "url": project_url,
                })
                count += 1

            position += 1

        print(f"  Projects on page {page_num}: {count} | Total: {len(projects)}")

        if done or test_mode or count < 32:
            break

        page_num += 1
        time.sleep(2)

    return projects


def main():
    test_mode = "--test" in sys.argv

    if test_mode:
        print("TEST MODE — first page only\n")

    projects = scrape_open_agents(test_mode)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(projects)} projects saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
