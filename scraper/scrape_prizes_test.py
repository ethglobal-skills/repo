"""
Test scraper for a single event prizes page.
Prints the full HTML of the first real sponsor section.

Usage:
  python scrape_prizes_test.py
"""

import requests
from bs4 import BeautifulSoup

URL = "https://ethglobal.com/events/hackmoney2026/prizes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

response = requests.get(URL, headers=HEADERS, timeout=15)
soup = BeautifulSoup(response.text, "lxml")

# Find all sponsor h2 sections, skip Finalists
sponsor_headings = [
    h for h in soup.find_all("h2", class_="mt-4 text-4xl font-semibold xl:pr-28")
    if "finalist" not in h.get_text(strip=True).lower()
]

print(f"Sponsor sections found: {len(sponsor_headings)}")
for h in sponsor_headings:
    print(f"  {h.get_text(strip=True)}")

# Walk up from the h2 to find the full sponsor container
first = sponsor_headings[0]
print(f"\n=== FULL SECTION: {first.get_text(strip=True)} ===")

# Walk up ancestors until we find one large enough to contain About/Prizes
node = first
for _ in range(8):
    node = node.parent
    text = node.get_text(strip=True)
    print(f"  ancestor <{node.name}> class={node.get('class')} | len={len(text)}")
    if len(text) > 2000:
        print(f"\n  --> Using this ancestor. HTML preview (first 8000 chars):")
        print(str(node)[:8000])
        break
