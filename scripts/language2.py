#!/usr/bin/env python3
"""Scrape top 1000 words from Wiktionary frequency lists using correct page names."""
import json
import urllib.request
import re
import time

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/language_learning.json"

# Correct page names found via search
LANGUAGES = {
    "Spanish": ["Wiktionary:Frequency lists/Spanish/Subtitles10K"],
    "French": ["Wiktionary:French frequency lists (Belgium, finance)/1-1000"],
    "German": ["Wiktionary:Frequency lists/German/TV and movie subtitles (2009)"],
    "Italian": ["Wiktionary:Frequency lists/Italian"],
    "Portuguese": ["Wiktionary:Frequency lists/Portuguese wordlist"],
    "Japanese": ["Wiktionary:Frequency lists/Japanese/5000 Most Frequent Words"],
    "Korean": ["Wiktionary:Frequency lists/Korean 5800"],
    "Mandarin Chinese": ["Wiktionary:Frequency lists/Mandarin"],
}

def get_wikitext(title):
    encoded = urllib.request.quote(title)
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if "parse" in data:
        return data["parse"]["wikitext"]["*"]
    return None

def extract_words(wikitext, limit=1200):
    """Extract words from wikitext. Various formats used across pages."""
    words = []
    seen = set()
    
    # Pattern 1: table rows with rank | word | translation
    # e.g. | 1 || [[hola]] || hello
    table_rows = re.findall(r'\|\|?\s*\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', wikitext)
    
    # Pattern 2: numbered list with [[word]] 
    # e.g. # [[word]] - meaning
    list_items = re.findall(r'#\s*\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', wikitext)
    
    # Pattern 3: just [[word]] links in order
    all_links = re.findall(r'\[\[([^\]|:#]+?)(?:\|[^\]]+?)?\]\]', wikitext)
    
    # Try table rows first, then list, then all links
    candidates = table_rows or list_items or all_links
    
    for w in candidates:
        w = w.strip()
        if (w and w not in seen and len(w) < 40 and 
            not w.startswith(('Wiktionary', 'Category', 'Appendix', 'w:', 'File', 'Image')) and
            not any(c in w for c in ['/', '{', '}', '='])):
            seen.add(w)
            words.append(w)
            if len(words) >= limit:
                break
    
    return words

def get_translation(word, lang):
    """Get English translation from Wiktionary entry."""
    encoded = urllib.request.quote(word)
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if "parse" not in data:
            return None
        text = data["parse"]["wikitext"]["*"]
        
        # Look for definition lines: # [[meaning]] or # meaning
        defs = re.findall(r'#\s*(?:\{\{[^}]*\}\}\s*)*(?:\[\[([^\]]+?)\]\]|([A-Za-z][\w\s,;]+))', text)
        for d in defs:
            meaning = (d[0] or d[1]).strip()
            # Clean up template residue
            meaning = re.sub(r'\{\{[^}]*\}\}', '', meaning).strip()
            if meaning and len(meaning) < 80 and not meaning.startswith(('#', '*', '{')):
                return meaning
        
        # Look for {{t|en|word}} translation templates
        trans = re.findall(r'\{\{t\+?\|en\|([^}|]+)', text)
        if trans:
            return trans[0].strip()
            
    except:
        pass
    return None

all_words = []

for lang, pages in LANGUAGES.items():
    print(f"\n{'='*50}")
    print(f"Processing {lang}...")
    
    words = []
    for page in pages:
        print(f"  Fetching: {page}")
        try:
            wikitext = get_wikitext(page)
            if not wikitext:
                print(f"  Page not found!")
                continue
            extracted = extract_words(wikitext, 1200)
            print(f"  Extracted {len(extracted)} words")
            words.extend(extracted)
        except Exception as e:
            print(f"  Error: {e}")
    
    if not words:
        print(f"  No words found for {lang}, skipping")
        continue
    
    # Translate top 1000
    words = words[:1000]
    translated_count = 0
    for i, word in enumerate(words):
        time.sleep(0.15)
        trans = get_translation(word, lang)
        entry = {
            "word": word,
            "english": trans or "",
            "language": lang,
            "rank": i + 1
        }
        all_words.append(entry)
        if trans:
            translated_count += 1
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(words)}: {translated_count} translated")
    
    print(f"  Done: {len(words)} words, {translated_count} translated")

print(f"\n{'='*50}")
print(f"Total entries: {len(all_words)}")
by_lang = {}
for w in all_words:
    lang = w["language"]
    by_lang.setdefault(lang, {"total": 0, "translated": 0})
    by_lang[lang]["total"] += 1
    if w["english"]:
        by_lang[lang]["translated"] += 1

for lang, stats in by_lang.items():
    print(f"  {lang}: {stats['total']} words ({stats['translated']} translated)")

with open(OUTPUT, "w") as f:
    json.dump(all_words, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {OUTPUT}")
