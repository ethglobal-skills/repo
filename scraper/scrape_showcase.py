"""
Scrapes all pages of https://ethglobal.com/showcase until a page returns
fewer than 32 projects (indicating the last page).
Output: data/projects_raw.json

Each entry:
  { "title": "...", "event": "...", "url": "..." }

Position 32 on each page is a duplicate of the first project on the next page — skipped.
"""

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ethglobal.com"
OUTPUT_FILE = Path(__file__).parent / "data" / "projects_raw.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_showcase() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    projects: list[dict] = []
    page_num = 1

    while True:
        print(f"\n=== Processing page {page_num} ===")
        url = f"{BASE_URL}/showcase?page={page_num}"

        response = session.get(url, timeout=15)
        if response.status_code != 200:
            print(f"  Got status {response.status_code}, stopping.")
            break

        soup = BeautifulSoup(response.text, "lxml")

        all_links = soup.find_all("a")
        count = 0
        position = 0

        for link in all_links:
            href = link.get("href", "")
            if not href.startswith("/showcase/"):
                continue

            # Skip the duplicate (position 32 == first project of next page)
            if position == 32:
                position += 1
                continue

            project_url = f"{BASE_URL}{href}"

            h2 = link.find("h2")
            title = h2.text.strip() if h2 else None

            div = link.find("div")
            event = div.text.strip() if div else None

            if title:
                projects.append({
                    "title": title,
                    "event": event,
                    "url": project_url,
                })
                count += 1

            position += 1

        print(f"  Projects on page {page_num}: {count} | Running total: {len(projects)}")

        # Fewer than 32 means this was the last page
        if count < 32:
            print("  Last page reached.")
            break

        page_num += 1
        time.sleep(2)

    return projects


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    projects = scrape_showcase()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(projects)} projects saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
