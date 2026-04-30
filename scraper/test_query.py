"""
Test query: find ETHGlobal Taipei projects that won World's Most Best Mini App prize.
"""

import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# 1. Find the event
event = supabase.table("events").select("id, name").ilike("name", "%taipei%").execute()
print("Events:", json.dumps(event.data, indent=2))

if not event.data:
    print("No event found.")
    exit()

event_id = event.data[0]["id"]

# 2. Find the sponsor
sponsor = supabase.table("sponsors").select("id, name").ilike("name", "%world%").execute()
print("\nSponsors:", json.dumps(sponsor.data, indent=2))
sponsor_id = sponsor.data[0]["id"] if sponsor.data else None

# 3. Find the prize
prize = (
    supabase.table("prizes")
    .select("id, title, sponsors(name)")
    .eq("event_id", event_id)
    .ilike("title", "%best mini app%")
    .execute()
)
if sponsor_id:
    prize.data = [p for p in prize.data if p["sponsors"]["name"] == sponsor.data[0]["name"]]
print("\nPrizes:", json.dumps(prize.data, indent=2))

if not prize.data:
    print("No prize found.")
    exit()

prize_ids = [p["id"] for p in prize.data]

# 3. Find projects that won any of these prizes
results = (
    supabase.table("project_prizes")
    .select("projects(title, url, tagline), prizes(title)")
    .in_("prize_id", prize_ids)
    .execute()
)
print("\nProjects that won:")
for r in results.data:
    p = r["projects"]
    prize_title = r["prizes"]["title"]
    print(f"  [{prize_title}] {p['title']} — {p['url']}")
    print(f"  {p['tagline']}\n")
