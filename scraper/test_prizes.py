"""
Test query: given an event and sponsor, return bounty descriptions and qualifications.
"""

import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

EVENT = "ethglobal taipei"
SPONSOR = "world"

# Find event
event = supabase.table("events").select("id, name").ilike("name", f"%{EVENT}%").execute()
event_id = event.data[0]["id"]
print(f"Event: {event.data[0]['name']} (id={event_id})\n")

# Find sponsor
sponsor = supabase.table("sponsors").select("id, name").ilike("name", f"%{SPONSOR}%").execute()
sponsor_id = sponsor.data[0]["id"]
print(f"Sponsor: {sponsor.data[0]['name']} (id={sponsor_id})\n")

# Get prizes
prizes = (
    supabase.table("prizes")
    .select("title, description, qualifications, prize_pool, amount")
    .eq("event_id", event_id)
    .eq("sponsor_id", sponsor_id)
    .execute()
)

import re
ORDINAL_RE = re.compile(r"\s*\d+(?:st|nd|rd|th)\s+place\s*$", re.IGNORECASE)

def base_title(title: str) -> str:
    return ORDINAL_RE.sub("", title).strip()

# Deduplicate: one entry per unique base title
seen = set()
unique_prizes = []
for p in prizes.data:
    key = base_title(p["title"]).lower()
    if key not in seen:
        seen.add(key)
        p["title"] = base_title(p["title"])
        unique_prizes.append(p)

print(f"{len(unique_prizes)} unique bounties (from {len(prizes.data)} prize records):\n")
for p in unique_prizes:
    print(f"  Title: {p['title']}")
    print(f"  Description: {p['description']}")
    print(f"  Qualifications: {p['qualifications']}")
    print(f"  Pool: {p['prize_pool']} | Amount: {p['amount']}")
    print()
