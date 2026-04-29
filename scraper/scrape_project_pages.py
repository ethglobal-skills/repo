"""
Scrapes individual project pages from ethglobal.com/showcase/{slug}.
Reads URLs from data/projects_raw.json, writes to data/projects_full.json.

Each entry adds to the existing fields:
  tagline, live_demo, github, description, how_its_made,
  prizes: [{ prize_image, prize_title, prize_pool }]

Run in test mode first:
  python scrape_project_pages.py --test
"""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ethglobal.com"
INPUT_FILE = Path(__file__).parent / "data" / "projects_raw.json"
OUTPUT_FILE = Path(__file__).parent / "data" / "projects_full.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TEST_URL = "https://ethglobal.com/showcase/opinionswap-7i953"


def scrape_project(session: requests.Session, url: str) -> dict:
    response = session.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    # --- Tagline ---
    # Usually a short italic or subtitle line near the top
    tagline = None
    for tag in soup.find_all(["p", "h2", "h3", "em", "i"]):
        text = tag.get_text(strip=True)
        if text and 20 < len(text) < 200:
            tagline = text
            break

    # --- Links ---
    live_demo = None
    github = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if not github and "github.com" in href:
            github = href
        if not live_demo and ("demo" in text or "live" in text or "website" in text or "app" in text):
            if not href.startswith("/") and "ethglobal" not in href:
                live_demo = href

    # --- Description & How It's Made ---
    description = None
    how_its_made = None

    for h3 in soup.find_all("h3", class_="my-4 text-xl font-semibold"):
        heading_text = h3.get_text(strip=True)
        # Collect all sibling text nodes until the next heading
        siblings = []
        for sibling in h3.next_siblings:
            if sibling.name in ["h2", "h3", "h4"]:
                break
            if hasattr(sibling, "get_text"):
                text = sibling.get_text(separator="\n", strip=True)
                if text:
                    siblings.append(text)
        body = "\n".join(siblings)

        if heading_text == "Project Description":
            description = body
        elif heading_text == "How it's Made":
            how_its_made = body

    # --- Prizes ---
    prizes = []
    winner_heading = soup.find(
        "h3",
        class_="text-black-500 uppercase text-xs font-normal mt-6 mb-2",
        string=lambda t: t and "Winner of" in t,
    )
    if winner_heading:
        prize_container = winner_heading.find_next_sibling("div", class_="space-y-3")
        if prize_container:
            for block in prize_container.find_all("div", class_="flex items-center"):
                img = block.find("img")
                prize_image = img.get("src", "") if img else ""
                title_div = block.find("div", class_="flex-1 mx-4")
                prize_title = title_div.get_text(strip=True) if title_div else block.get_text(strip=True)
                prize_pool = "pool" in prize_title.lower()
                if prize_title:
                    prizes.append({
                        "prize_image": prize_image,
                        "prize_title": prize_title,
                        "prize_pool": prize_pool,
                    })

    return {
        "tagline": tagline or "",
        "live_demo": live_demo or "",
        "github": github or "",
        "description": description or "",
        "how_its_made": how_its_made or "",
        "prizes": prizes,
    }


def main():
    test_mode = "--test" in sys.argv

    session = requests.Session()
    session.headers.update(HEADERS)

    if test_mode:
        print(f"TEST MODE — scraping {TEST_URL}\n")
        result = scrape_project(session, TEST_URL)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    limit = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    with open(INPUT_FILE) as f:
        data = json.load(f)

    projects = data["projects"]
    if limit:
        projects = projects[:limit]
    print(f"Scraping {len(projects)} project pages...")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    enriched = []
    for i, project in enumerate(projects, 1):
        print(f"[{i}/{len(projects)}] {project['title']}")
        try:
            details = scrape_project(session, project["url"])
            enriched.append({**project, **details})
        except Exception as e:
            print(f"  Error: {e}")
            enriched.append(project)
        time.sleep(2)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"projects": enriched}, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(enriched)} projects saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
