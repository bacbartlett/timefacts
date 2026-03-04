#!/usr/bin/env python3
"""Fetch quotes from Hugging Face datasets API."""
import json
import urllib.request

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/inspirational_quotes.json"

all_quotes = []
seen = set()

# Source 1: Abirate/english_quotes (2508 quotes)
print("Fetching Abirate/english_quotes from HuggingFace...")
offset = 0
while True:
    url = f"https://datasets-server.huggingface.co/rows?dataset=Abirate/english_quotes&config=default&split=train&offset={offset}&length=100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    rows = data.get("rows", [])
    if not rows:
        break
    for r in rows:
        row = r["row"]
        q = row.get("quote", "").strip().strip('"').strip('\u201c\u201d')
        a = row.get("author", "Unknown").strip()
        tags = row.get("tags", [])
        if q and q not in seen:
            seen.add(q)
            all_quotes.append({"quote": q, "author": a, "tags": tags, "source": "english_quotes"})
    offset += 100
    if offset % 500 == 0:
        print(f"  {offset}: {len(all_quotes)} quotes")

print(f"After english_quotes: {len(all_quotes)}")

# Source 2: quote-dataset on HuggingFace (larger)
print("\nFetching Abirate/english_quotes done. Trying other datasets...")

for dataset in ["dwarkesh/quotes", "noahkim/QuoteDB"]:
    print(f"\nTrying {dataset}...")
    offset = 0
    count_before = len(all_quotes)
    try:
        while offset < 10000:
            url = f"https://datasets-server.huggingface.co/rows?dataset={dataset}&config=default&split=train&offset={offset}&length=100"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            rows = data.get("rows", [])
            if not rows:
                break
            for r in rows:
                row = r["row"]
                # Try common column names
                q = row.get("quote", row.get("Quote", row.get("text", ""))).strip().strip('"').strip('\u201c\u201d')
                a = row.get("author", row.get("Author", row.get("source", "Unknown"))).strip()
                if q and q not in seen and len(q) > 10:
                    seen.add(q)
                    all_quotes.append({"quote": q, "author": a, "source": dataset})
            offset += 100
        print(f"  Got {len(all_quotes) - count_before} new from {dataset}")
    except Exception as e:
        print(f"  Error: {e}")

# Source 3: ZenQuotes (what we can get)
print("\nFetching from ZenQuotes...")
try:
    url = "https://zenquotes.io/api/quotes"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    batch = json.loads(resp.read())
    for q in batch:
        text = q.get("q", "").strip()
        author = q.get("a", "Unknown").strip()
        if text and text not in seen and not text.startswith("Too many"):
            seen.add(text)
            all_quotes.append({"quote": text, "author": author, "source": "zenquotes"})
    print(f"  ZenQuotes added: now {len(all_quotes)}")
except Exception as e:
    print(f"  ZenQuotes: {e}")

print(f"\n{'='*50}")
print(f"Total unique quotes: {len(all_quotes)}")

with open(OUTPUT, "w") as f:
    json.dump(all_quotes, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
