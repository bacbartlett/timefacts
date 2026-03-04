#!/usr/bin/env python3
"""Scrape inspirational quotes from multiple sources."""
import json
import urllib.request
import re
import time

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/inspirational_quotes.json"

all_quotes = []
seen = set()

def add_quote(text, author, source):
    text = text.strip().strip('"').strip('"').strip('"').strip()
    if text and text not in seen and len(text) > 10 and len(text) < 500:
        seen.add(text)
        all_quotes.append({"quote": text, "author": author.strip(), "source": source})

# Source 1: ZenQuotes (already got ~241)
print("Source 1: ZenQuotes API...")
try:
    for i in range(3):
        url = "https://zenquotes.io/api/quotes"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        batch = json.loads(resp.read())
        for q in batch:
            if q.get("q") and not q["q"].startswith("Too many"):
                add_quote(q["q"], q.get("a", "Unknown"), "zenquotes")
        time.sleep(2)
except Exception as e:
    print(f"  ZenQuotes: {e}")
print(f"  After ZenQuotes: {len(all_quotes)}")

# Source 2: quotable.io (if available)
print("Source 2: quotable API...")
try:
    for page in range(1, 100):
        url = f"https://api.quotable.io/quotes?page={page}&limit=150"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            break
        for q in results:
            add_quote(q["content"], q["author"], "quotable")
        if page % 20 == 0:
            print(f"  Page {page}: {len(all_quotes)} total")
        time.sleep(0.2)
except Exception as e:
    print(f"  quotable: {e}")
print(f"  After quotable: {len(all_quotes)}")

# Source 3: Kaggle-style - scrape brainyquote topics
print("Source 3: BrainyQuote topics...")
topics = ["inspirational", "motivational", "life", "wisdom", "positive", 
          "success", "happiness", "love", "strength", "courage",
          "hope", "faith", "dreams", "leadership", "change",
          "attitude", "perseverance", "determination", "believe", "passion"]

for topic in topics:
    for page in range(1, 6):  # 5 pages per topic
        try:
            url = f"https://www.brainyquote.com/topics/{topic}-quotes_{page}" if page > 1 else f"https://www.brainyquote.com/topics/{topic}-quotes"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
            resp = urllib.request.urlopen(req, timeout=30)
            html = resp.read().decode("utf-8", errors="ignore")
            
            # Extract quotes from BrainyQuote HTML
            # Pattern: <a ... class="b-qt" ...>quote text</a>
            quotes = re.findall(r'class="b-qt[^"]*"[^>]*>([^<]+)</a>', html)
            authors = re.findall(r'class="bq-aut[^"]*"[^>]*>([^<]+)</a>', html)
            
            for i, q in enumerate(quotes):
                author = authors[i] if i < len(authors) else "Unknown"
                add_quote(q, author, f"brainyquote/{topic}")
            
            time.sleep(1)
        except Exception as e:
            if "403" in str(e) or "429" in str(e):
                time.sleep(5)
                break
            pass
    
    print(f"  Topic '{topic}': {len(all_quotes)} total")

# Source 4: goodreads quotes pages
print("Source 4: Goodreads popular quotes...")
for page in range(1, 51):
    try:
        url = f"https://www.goodreads.com/quotes?page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        resp = urllib.request.urlopen(req, timeout=30)
        html = resp.read().decode("utf-8", errors="ignore")
        
        # Goodreads pattern: <div class="quoteText">  "quote" ... ― Author
        blocks = re.findall(r'class="quoteText"[^>]*>\s*(?:&ldquo;)?\s*(.+?)\s*(?:&rdquo;)?\s*<br', html, re.DOTALL)
        author_blocks = re.findall(r'class="authorOrTitle"[^>]*>\s*(.+?)\s*</span>', html)
        
        for i, q in enumerate(blocks):
            q = re.sub(r'<[^>]+>', '', q).strip().strip('\u201c\u201d"\'')
            author = author_blocks[i].strip().rstrip(',') if i < len(author_blocks) else "Unknown"
            author = re.sub(r'<[^>]+>', '', author).strip()
            add_quote(q, author, "goodreads")
        
        if page % 10 == 0:
            print(f"  Page {page}: {len(all_quotes)} total")
        time.sleep(1.5)
    except Exception as e:
        if "403" in str(e) or "429" in str(e):
            print(f"  Rate limited at page {page}")
            time.sleep(10)
        pass

print(f"  After Goodreads: {len(all_quotes)}")

print(f"\n{'='*50}")
print(f"Total unique inspirational quotes: {len(all_quotes)}")

with open(OUTPUT, "w") as f:
    json.dump(all_quotes, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
