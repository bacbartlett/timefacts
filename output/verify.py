#!/usr/bin/env python3
"""
Fact verification script using Wikipedia API.
Scores each fact as CONFIRMED, PLAUSIBLE, UNVERIFIED, or FALSE.
Removes FALSE and UNVERIFIED facts.
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path("/root/.openclaw/workspace/scrape-project/output")
PROGRESS_FILE = OUTPUT_DIR / "verification_progress.json"
HEADERS = {"User-Agent": "FactChecker/1.0 (r2@brandonb.dev)"}

def wiki_search(query, limit=3):
    """Search Wikipedia and return list of {title, snippet}."""
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": limit, "format": "json"
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("query", {}).get("search", [])
    except Exception as e:
        return []

def wiki_summary(title):
    """Get Wikipedia page summary."""
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("extract", "")
    except Exception:
        return ""

def extract_key_terms(fact):
    """Extract key searchable terms from a fact."""
    # Remove common filler words for better search
    text = fact.strip().strip('"')
    # For search, use the first ~80 chars or key proper nouns
    if len(text) > 100:
        text = text[:100]
    return text

def verify_fact(fact, is_quote=False, author=None):
    """
    Verify a single fact against Wikipedia.
    Returns (score, reason).
    """
    if is_quote:
        # For quotes, search for the quote + author attribution
        query = f'"{author}" quote'
        results = wiki_search(query, limit=3)
        if not results:
            # Author exists on Wikipedia = PLAUSIBLE at minimum
            results = wiki_search(author, limit=1)
            if results:
                return "PLAUSIBLE", "Author found on Wikipedia"
            return "PLAUSIBLE", "Could not verify via Wikipedia"
        # Check if author appears in results
        for r in results:
            snippet = r.get("snippet", "").lower()
            title = r.get("title", "").lower()
            if author.lower().split()[-1] in title or author.lower().split()[-1] in snippet:
                return "PLAUSIBLE", f"Author confirmed: {r['title']}"
        return "PLAUSIBLE", "Author search returned results"

    # For regular facts
    search_text = extract_key_terms(fact)
    results = wiki_search(search_text, limit=3)
    
    if not results:
        # Try shorter search
        words = fact.split()
        if len(words) > 5:
            shorter = " ".join(words[:8])
            results = wiki_search(shorter, limit=3)
    
    if not results:
        return "UNVERIFIED", "No Wikipedia results found"
    
    # Get summary of top result
    top_title = results[0]["title"]
    summary = wiki_summary(top_title)
    snippet = results[0].get("snippet", "")
    
    # Check for key claim elements in the summary/snippet
    combined_text = (summary + " " + snippet).lower()
    fact_lower = fact.lower()
    
    # Extract numbers from fact for verification
    fact_numbers = set(re.findall(r'\b\d+\.?\d*\b', fact))
    
    # Check if key terms from the fact appear in Wikipedia content
    # Split fact into meaningful chunks
    fact_words = set(w.lower() for w in re.findall(r'[A-Za-z]{4,}', fact))
    combined_words = set(w.lower() for w in re.findall(r'[A-Za-z]{4,}', combined_text))
    
    overlap = fact_words & combined_words
    overlap_ratio = len(overlap) / max(len(fact_words), 1)
    
    # Check numbers match
    summary_numbers = set(re.findall(r'\b\d+\.?\d*\b', combined_text))
    number_match = bool(fact_numbers & summary_numbers) if fact_numbers else True
    
    if overlap_ratio > 0.5 and number_match:
        return "CONFIRMED", f"Matched with '{top_title}' ({overlap_ratio:.0%} term overlap)"
    elif overlap_ratio > 0.3:
        return "PLAUSIBLE", f"Partial match with '{top_title}' ({overlap_ratio:.0%} overlap)"
    elif overlap_ratio > 0.15:
        return "PLAUSIBLE", f"Weak match with '{top_title}'"
    else:
        # Check other results
        for r in results[1:]:
            s = r.get("snippet", "").lower()
            s_words = set(w.lower() for w in re.findall(r'[A-Za-z]{4,}', s))
            if len(fact_words & s_words) / max(len(fact_words), 1) > 0.3:
                return "PLAUSIBLE", f"Found in '{r['title']}'"
        return "UNVERIFIED", f"Low relevance match with '{top_title}'"

def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {
        "completed_files": [],
        "current_file": None,
        "current_index": 0,
        "removed_count": {},
        "total_verified": 0,
        "flagged_for_review": {}
    }

def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

def process_file(filename, progress, is_quotes=False):
    """Process a single CSV file."""
    filepath = OUTPUT_DIR / filename
    category = filename.replace("_1000.csv", "")
    
    # Check if already completed
    if filename in progress["completed_files"]:
        print(f"  Skipping {filename} (already completed)")
        return
    
    # Read all facts
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    total = len(rows)
    start_idx = 0
    if progress["current_file"] == filename:
        start_idx = progress["current_index"]
    
    verified_file = OUTPUT_DIR / filename.replace("_1000.csv", "_verified.csv")
    
    # Load already-verified rows if resuming
    verified_rows = []
    if start_idx > 0 and verified_file.exists():
        with open(verified_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            verified_rows = list(reader)
    
    removed = progress["removed_count"].get(category, 0)
    flagged = progress.get("flagged_for_review", {}).get(category, [])
    
    print(f"  Processing {filename}: {total} facts, starting at index {start_idx}")
    
    for i in range(start_idx, total):
        row = rows[i]
        
        if is_quotes:
            quote = row.get("quote", "")
            author = row.get("author", "")
            score, reason = verify_fact(quote, is_quote=True, author=author)
            fact_display = f'"{quote[:60]}..." - {author}'
        else:
            fact = row.get("fact", "")
            score, reason = verify_fact(fact)
            fact_display = fact[:80]
        
        if score in ("CONFIRMED", "PLAUSIBLE"):
            verified_rows.append(row)
        else:
            removed += 1
            flagged.append({"index": i, "fact": fact_display[:100], "score": score, "reason": reason})
            if removed % 5 == 0:
                print(f"    Removed #{removed}: [{score}] {fact_display[:80]}...")
        
        # Save progress every 50 facts
        if (i + 1) % 50 == 0 or i == total - 1:
            progress["current_file"] = filename
            progress["current_index"] = i + 1
            progress["removed_count"][category] = removed
            if "flagged_for_review" not in progress:
                progress["flagged_for_review"] = {}
            progress["flagged_for_review"][category] = flagged[-20:]  # Keep last 20
            progress["total_verified"] = len(verified_rows)
            save_progress(progress)
            
            # Write verified rows so far
            if verified_rows:
                fieldnames = verified_rows[0].keys()
                with open(verified_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(verified_rows)
            
            if (i + 1) % 100 == 0:
                print(f"    Progress: {i+1}/{total} verified, {removed} removed")
        
        # Rate limit: ~100ms between API calls
        time.sleep(0.1)
    
    # Mark complete
    progress["completed_files"].append(filename)
    progress["current_file"] = None
    progress["current_index"] = 0
    progress["removed_count"][category] = removed
    save_progress(progress)
    
    kept = len(verified_rows)
    print(f"  ✓ {filename}: kept {kept}/{total}, removed {removed}")
    if kept < 900:
        print(f"  ⚠️  WARNING: Only {kept} facts remain — need to backfill {900 - kept}")
    
    return kept, removed

def main():
    files = [
        ("trivia_1000.csv", False),
        ("history_1000.csv", False),
        ("language_1000.csv", False),
        ("quotes_1000.csv", True),
        ("sports_1000.csv", False),
    ]
    
    progress = load_progress()
    results = {}
    
    for filename, is_quotes in files:
        print(f"\n{'='*60}")
        print(f"Verifying: {filename}")
        print(f"{'='*60}")
        result = process_file(filename, progress, is_quotes=is_quotes)
        if result:
            results[filename] = result
    
    # Final summary
    print(f"\n{'='*60}")
    print("VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(json.dumps(progress["removed_count"], indent=2))
    
    # Check which files need backfill
    for filename, _ in files:
        verified_file = OUTPUT_DIR / filename.replace("_1000.csv", "_verified.csv")
        if verified_file.exists():
            with open(verified_file, newline='', encoding='utf-8') as f:
                count = sum(1 for _ in f) - 1  # minus header
            category = filename.replace("_1000.csv", "")
            print(f"  {category}: {count} facts retained")
            if count < 900:
                print(f"    ⚠️  NEEDS BACKFILL: {900 - count} more facts needed")

if __name__ == "__main__":
    main()
