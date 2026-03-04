#!/usr/bin/env python3
"""
Fetch top 1000 frequency words per language from FrequencyWords (GitHub),
then batch-translate via MyMemory API (free, no key needed).
"""
import json
import urllib.request
import urllib.parse
import time

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/language_learning.json"

# FrequencyWords repo: hermitdave/FrequencyWords
BASE = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018"

LANGUAGES = {
    "Spanish": {"code": "es", "mymemory": "es|en"},
    "French": {"code": "fr", "mymemory": "fr|en"},
    "German": {"code": "de", "mymemory": "de|en"},
    "Italian": {"code": "it", "mymemory": "it|en"},
    "Portuguese": {"code": "pt", "mymemory": "pt|en"},
    "Japanese": {"code": "ja", "mymemory": "ja|en"},
    "Korean": {"code": "ko", "mymemory": "ko|en"},
    "Mandarin Chinese": {"code": "zh", "mymemory": "zh-CN|en"},
}

def fetch_frequency_list(lang_code, limit=1200):
    """Fetch top N words from FrequencyWords."""
    url = f"{BASE}/{lang_code}/{lang_code}_50k.txt"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    text = resp.read().decode("utf-8")
    
    words = []
    for line in text.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 1:
            word = parts[0]
            # Skip very short words (articles, etc) and non-alpha for latin scripts
            if len(word) >= 2:
                words.append(word)
        if len(words) >= limit:
            break
    return words

def translate_batch(words, langpair, batch_size=10):
    """Translate words using MyMemory API (free, 5000 chars/day per IP)."""
    translations = {}
    
    for i in range(0, len(words), batch_size):
        batch = words[i:i+batch_size]
        # Join with | separator for batch query
        text = "\n".join(batch)
        encoded = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair={langpair}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            
            translated_text = data.get("responseData", {}).get("translatedText", "")
            if translated_text:
                trans_words = translated_text.split("\n")
                for j, w in enumerate(batch):
                    if j < len(trans_words):
                        t = trans_words[j].strip()
                        # Only keep if actually different from source
                        if t.lower() != w.lower():
                            translations[w] = t
            
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            # Fall back to one-at-a-time
            for w in batch:
                try:
                    encoded = urllib.parse.quote(w)
                    url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair={langpair}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    resp = urllib.request.urlopen(req, timeout=10)
                    data = json.loads(resp.read())
                    t = data.get("responseData", {}).get("translatedText", "").strip()
                    if t and t.lower() != w.lower():
                        translations[w] = t
                    time.sleep(0.3)
                except:
                    pass
        
        if (i + batch_size) % 100 == 0:
            print(f"    Translated {min(i+batch_size, len(words))}/{len(words)}")
    
    return translations

all_words = []

for lang, config in LANGUAGES.items():
    print(f"\n{'='*50}")
    print(f"{lang} ({config['code']})")
    
    # Fetch frequency list
    try:
        words = fetch_frequency_list(config["code"], 1200)
        print(f"  Fetched {len(words)} words")
    except Exception as e:
        print(f"  Failed to fetch: {e}")
        continue
    
    # Translate
    print(f"  Translating via MyMemory ({config['mymemory']})...")
    translations = translate_batch(words[:1000], config["mymemory"])
    print(f"  Got {len(translations)} translations")
    
    # Build entries
    for i, word in enumerate(words[:1000]):
        all_words.append({
            "word": word,
            "english": translations.get(word, ""),
            "language": lang,
            "rank": i + 1
        })

# Summary
print(f"\n{'='*50}")
print(f"Total entries: {len(all_words)}")
by_lang = {}
for w in all_words:
    l = w["language"]
    by_lang.setdefault(l, {"total": 0, "translated": 0})
    by_lang[l]["total"] += 1
    if w["english"]:
        by_lang[l]["translated"] += 1

for l, s in by_lang.items():
    print(f"  {l}: {s['total']} words ({s['translated']} with translations)")

with open(OUTPUT, "w") as f:
    json.dump(all_words, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {OUTPUT}")
