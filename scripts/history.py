#!/usr/bin/env python3
"""Scrape American history factoids from Wikipedia 'On This Day' and history.muffinlabs.com."""
import json
import urllib.request
import time
import re

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/american_history.json"

all_facts = []
seen = set()

# Source 1: history.muffinlabs.com - Wikipedia parsed history for each day
print("Fetching from history.muffinlabs.com (all 366 days)...")

months_days = [
    (1,31),(2,29),(3,31),(4,30),(5,31),(6,30),
    (7,31),(8,31),(9,30),(10,31),(11,30),(12,31)
]

american_keywords = [
    "united states", "american", "america", "u.s.", "congress", "president",
    "washington", "new york", "california", "texas", "virginia", "massachusetts",
    "philadelphia", "boston", "chicago", "colonial", "independence", "constitution",
    "amendment", "supreme court", "civil war", "revolutionary", "confederate",
    "union army", "declaration", "lincoln", "jefferson", "roosevelt", "kennedy",
    "nasa", "apollo", "pearl harbor", "gettysburg", "emancipation",
    "white house", "pentagon", "senate", "house of representatives",
    "mississippi", "ohio", "michigan", "florida", "illinois", "georgia",
    "louisiana", "maryland", "connecticut", "native american", "indian",
    "slavery", "abolition", "reconstruction", "prohibition", "new deal",
    "cold war", "vietnam", "korean war", "d-day", "normandy",
    "martin luther king", "rosa parks", "selma", "montgomery",
    "wall street", "great depression", "dust bowl", "gold rush",
    "lewis and clark", "manifest destiny", "oregon trail",
    "wright brothers", "edison", "ford", "carnegie", "rockefeller",
    "ellis island", "statue of liberty", "alamo", "jamestown", "plymouth",
    "mayflower", "thanksgiving", "bill of rights", "federalist",
    "democrat", "republican", "whig", "electoral", "inaugur"
]

for month, days in months_days:
    for day in range(1, days + 1):
        url = f"http://history.muffinlabs.com/date/{month}/{day}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            
            events = data.get("data", {}).get("Events", [])
            for event in events:
                text = event.get("text", "").strip()
                year = event.get("year", "")
                full_text = f"{year}: {text}" if year else text
                
                # Filter for American history
                text_lower = full_text.lower()
                if any(kw in text_lower for kw in american_keywords):
                    if full_text not in seen:
                        seen.add(full_text)
                        all_facts.append({
                            "fact": full_text,
                            "year": year,
                            "date": f"{month}/{day}",
                            "source": "wikipedia/muffinlabs"
                        })
            
            time.sleep(0.3)  # Be nice
            
        except Exception as e:
            if "429" in str(e) or "Too Many" in str(e):
                print(f"  Rate limited at {month}/{day}, waiting 10s...")
                time.sleep(10)
                continue
            print(f"  Error on {month}/{day}: {e}")
        
        if (month == 1 and day % 10 == 0) or day == 1:
            print(f"  Month {month}, Day {day}: {len(all_facts)} facts so far")

    print(f"Month {month} done: {len(all_facts)} total facts")

print(f"\n{'='*50}")
print(f"Total American history facts: {len(all_facts)}")

with open(OUTPUT, "w") as f:
    json.dump(all_facts, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
