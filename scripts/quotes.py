#!/usr/bin/env python3
"""Download Quotes-500K and filter for inspirational quotes."""
import csv
import json
import os
import urllib.request
import zipfile
import io

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/inspirational_quotes.json"

# Quotes-500K is on Google Drive - let's try the direct download
# Alternative: scrape from brainyquote/goodreads style sites
# First, let's try a simpler high-quality source: type.fit quotes API
print("Fetching quotes from type.fit API...")
url = "https://type.fit/api/quotes"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    print(f"Got {len(data)} quotes from type.fit")
except Exception as e:
    print(f"type.fit failed: {e}")
    data = []

# Also scrape from quotable.io / zenquotes
print("Fetching from ZenQuotes API...")
zen_quotes = []
try:
    for i in range(50):  # 50 pages of 50 = 2500
        url = f"https://zenquotes.io/api/quotes"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        batch = json.loads(resp.read())
        if not batch or (len(batch) == 1 and batch[0].get("q", "").startswith("Too many")):
            print(f"ZenQuotes rate limited after {i} requests")
            break
        zen_quotes.extend(batch)
        if i % 10 == 0:
            print(f"  ZenQuotes batch {i}: {len(zen_quotes)} total")
except Exception as e:
    print(f"ZenQuotes error: {e}")

print(f"Got {len(zen_quotes)} quotes from ZenQuotes")

# Combine and deduplicate
all_quotes = []
seen = set()

for q in data:
    text = q.get("text", "").strip()
    author = (q.get("author") or "Unknown").strip().rstrip(", type.fit")
    if text and text not in seen:
        seen.add(text)
        all_quotes.append({"quote": text, "author": author, "source": "type.fit"})

for q in zen_quotes:
    text = q.get("q", "").strip()
    author = q.get("a", "Unknown").strip()
    if text and text not in seen:
        seen.add(text)
        all_quotes.append({"quote": text, "author": author, "source": "zenquotes"})

print(f"\nTotal unique quotes: {len(all_quotes)}")

with open(OUTPUT, "w") as f:
    json.dump(all_quotes, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
