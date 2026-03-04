#!/usr/bin/env python3
"""Scrape top 1000 common words from Wiktionary frequency lists for popular languages."""
import json
import urllib.request
import re
import time

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/language_learning.json"

# Wiktionary frequency list pages - these have top 1000-10000 words
# We'll scrape the wiki pages directly
LANGUAGES = {
    "Spanish": "Wiktionary:Frequency_lists/Spanish1000",
    "French": "Wiktionary:Frequency_lists/French_wordlist_opensubtitles_5000",
    "German": "Wiktionary:Frequency_lists/German_subtitles_1000",
    "Italian": "Wiktionary:Frequency_lists/Italian1000",
    "Portuguese": "Wiktionary:Frequency_lists/Portuguese_wordlist_opensubtitles_5000",
    "Japanese": "Wiktionary:Frequency_lists/Japanese",
    "Korean": "Wiktionary:Frequency_lists/Korean_5800",
    "Mandarin_Chinese": "Wiktionary:Frequency_lists/Mandarin",
}

# Alternative: use Wiktionary API to get page content
def get_wiktionary_page(title):
    """Fetch wiktionary page content via API."""
    encoded = urllib.request.quote(title)
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if "parse" in data:
        return data["parse"]["wikitext"]["*"]
    return None

def get_wiktionary_html(title):
    """Fetch rendered HTML."""
    encoded = urllib.request.quote(title)
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}&prop=text&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if "parse" in data:
        return data["parse"]["text"]["*"]
    return None

def extract_words_from_wikitext(wikitext, limit=1000):
    """Extract words from wikitext - common patterns are [[word]] or table rows."""
    words = []
    # Pattern 1: [[word]] links
    links = re.findall(r'\[\[([^\]|#]+?)(?:\|[^\]]+?)?\]\]', wikitext)
    for w in links:
        w = w.strip()
        # Skip meta/category links
        if ':' in w or len(w) > 50 or w.startswith(('Wiktionary', 'Category', 'Appendix', '#')):
            continue
        if w and w not in [x['word'] for x in words]:
            words.append({"word": w})
        if len(words) >= limit:
            break
    return words

def get_translation(word, lang_code):
    """Get English translation from Wiktionary API."""
    encoded = urllib.request.quote(word)
    url = f"https://en.wiktionary.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if "parse" in data:
            text = data["parse"]["wikitext"]["*"]
            # Look for English translation patterns: # [[word]] or gloss
            definitions = re.findall(r'#\s*(?:\{\{[^}]*\}\}\s*)*\[\[([^\]]+)\]\]', text)
            if definitions:
                return definitions[0]
            # Simpler: look for {{t+|en|word}} or {{t|en|word}}
            trans = re.findall(r'\{\{t\+?\|en\|([^}|]+)', text)
            if trans:
                return trans[0]
            # Look for definition lines
            defs = re.findall(r'#\s*(.+?)(?:\n|$)', text)
            for d in defs:
                clean = re.sub(r'\{\{[^}]*\}\}', '', d)
                clean = re.sub(r'\[\[([^\]|]*?)(?:\|([^\]]*?))?\]\]', r'\2' if r'\2' else r'\1', clean)
                clean = clean.strip(' .,;:')
                if clean and len(clean) < 100:
                    return clean
    except:
        pass
    return None

all_words = {}

for lang, page_title in LANGUAGES.items():
    print(f"\n{'='*50}")
    print(f"Processing {lang}: {page_title}")
    
    try:
        wikitext = get_wiktionary_page(page_title)
        if not wikitext:
            print(f"  Could not fetch page, trying alternatives...")
            # Try common alternative page names
            alts = [
                f"Wiktionary:Frequency_lists/{lang}_1000",
                f"Wiktionary:Frequency_lists/{lang}1000",
                f"Appendix:{lang}_frequency_list",
            ]
            for alt in alts:
                wikitext = get_wiktionary_page(alt)
                if wikitext:
                    print(f"  Found at: {alt}")
                    break
        
        if not wikitext:
            print(f"  FAILED to find frequency list for {lang}")
            continue
            
        words = extract_words_from_wikitext(wikitext, limit=1000)
        print(f"  Extracted {len(words)} words")
        
        # Get translations for first 1000 words (with rate limiting)
        translated = []
        for i, w in enumerate(words[:1000]):
            time.sleep(0.2)  # Rate limit
            trans = get_translation(w["word"], lang.lower()[:2])
            entry = {
                "word": w["word"],
                "english": trans or "",
                "language": lang.replace("_", " "),
                "rank": i + 1
            }
            translated.append(entry)
            
            if (i + 1) % 100 == 0:
                print(f"  Translated {i+1}/{len(words[:1000])} ({sum(1 for t in translated if t['english'])}/{i+1} have translations)")
        
        all_words[lang] = translated
        print(f"  Final: {len(translated)} words, {sum(1 for t in translated if t['english'])} with translations")
        
    except Exception as e:
        print(f"  ERROR: {e}")
    
    time.sleep(1)

# Flatten for output
flat = []
for lang, words in all_words.items():
    flat.extend(words)

print(f"\n{'='*50}")
print(f"Total words across all languages: {len(flat)}")
for lang, words in all_words.items():
    with_trans = sum(1 for w in words if w["english"])
    print(f"  {lang}: {len(words)} words ({with_trans} translated)")

with open(OUTPUT, "w") as f:
    json.dump(flat, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {OUTPUT}")
