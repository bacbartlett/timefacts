#!/usr/bin/env python3
"""Generate 500 diverse language facts via Claude."""
import csv
import json
import urllib.request
import time
import re

API_KEY = "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"
MODEL = "anthropic/claude-sonnet-4"
OUTPUT = "/root/.openclaw/workspace/scrape-project/output/language_500.csv"

def call_llm(prompt, max_tokens=4000):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://brandonb.dev",
        }
    )
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    return None

CATEGORIES = [
    ("English etymology and word origins", 130, [
        "surprising English word origins", "words from unexpected languages",
        "words whose meanings changed dramatically", "compound words with hidden histories",
        "everyday words with fascinating backstories"
    ]),
    ("Facts about Japanese language and culture", 30, [
        "Japanese writing systems", "Japanese onomatopoeia", "unique Japanese words and concepts",
    ]),
    ("Facts about Mandarin Chinese", 30, [
        "Chinese characters and their logic", "tones and meaning in Mandarin", "Chinese idioms and their stories"
    ]),
    ("Facts about Arabic language", 25, [
        "Arabic root system", "Arabic calligraphy", "Arabic influence on other languages"
    ]),
    ("Facts about Spanish language", 20, [
        "Spanish dialects worldwide", "Spanish words from Arabic", "unique Spanish expressions"
    ]),
    ("Facts about French language", 20, [
        "French influence on English", "French linguistic quirks", "French Academy and language preservation"
    ]),
    ("Facts about German language", 20, [
        "German compound words", "German grammatical quirks", "German words English borrowed"
    ]),
    ("Facts about Korean language", 15, [
        "Hangul invention", "Korean honorifics", "Korean linguistic features"
    ]),
    ("Facts about Hindi and Indian languages", 15, [
        "Hindi-Urdu relationship", "Sanskrit influences", "Indian linguistic diversity"
    ]),
    ("Facts about African languages (Swahili, etc.)", 15, [
        "Swahili as a trade language", "click languages", "African language diversity"
    ]),
    ("Facts about other world languages (Turkish, Finnish, Icelandic, Hawaiian, etc.)", 20, [
        "unusual language features worldwide", "small endangered languages", "language isolates"
    ]),
    ("Writing systems and scripts", 60, [
        "alphabet origins and evolution", "unique writing systems (Cherokee, Hangul, Braille)",
        "hieroglyphics and ancient scripts", "how different scripts work (abjads, syllabaries, logographies)"
    ]),
    ("Linguistic phenomena and grammar quirks", 60, [
        "universal grammar features", "unusual phonemes", "language families and relationships",
        "how languages change over time", "pidgins and creoles", "whistled and signed languages"
    ]),
    ("Cross-language fun (false friends, untranslatable words, loanwords)", 40, [
        "false friends between languages", "untranslatable words from around the world",
        "surprising loanword journeys", "words that sound rude in other languages"
    ]),
]

all_facts = []

for category, count, subtopics in CATEGORIES:
    print(f"\n=== {category} ({count} facts) ===")
    
    # Generate in chunks of ~30
    remaining = count
    while remaining > 0:
        batch = min(remaining, 35)
        existing_sample = ""
        if all_facts:
            # Show some existing to avoid dupes
            recent = all_facts[-20:] if len(all_facts) > 20 else all_facts
            existing_sample = f"\n\nAlready generated (DO NOT REPEAT similar facts):\n" + "\n".join(f"- {f}" for f in recent)
        
        subtopic_str = ", ".join(subtopics)
        prompt = f"""Generate exactly {batch} fascinating facts about: {category}
Subtopics to cover: {subtopic_str}

Requirements:
- Each fact: 1-3 sentences (prefer 1, max 3). Short enough for an e-ink clock display.
- Must pass the "I want to tell someone this" test — genuinely surprising or delightful
- State facts POSITIVELY (no "X does not..." or "X is not...")
- Be ACCURATE — don't make things up. Stick to well-established linguistic facts.
- Vary sentence structure. Don't start every fact with "The word..."
- NO markdown, NO numbering, NO bullets
- Return as a JSON array of strings{existing_sample}

Return ONLY the JSON array, nothing else."""

        result = call_llm(prompt)
        if result is None:
            print(f"  Failed, retrying...")
            continue
        
        try:
            # Find JSON array
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                facts = json.loads(match.group())
            else:
                print(f"  No JSON found, retrying...")
                continue
        except json.JSONDecodeError:
            print(f"  JSON parse error, retrying...")
            continue
        
        # Basic quality filter
        good = []
        for f in facts:
            f = f.strip()
            if len(f) < 20 or len(f) > 350:
                continue
            if re.search(r'\b(does not|is not|isn\'t|doesn\'t|cannot|can\'t)\b', f.lower()):
                continue
            good.append(f)
        
        all_facts.extend(good[:batch])
        remaining -= len(good[:batch])
        print(f"  Got {len(good[:batch])}, remaining: {remaining}")
        time.sleep(1)

print(f"\n\nTotal facts generated: {len(all_facts)}")

# Trim or pad to exactly 500
if len(all_facts) > 500:
    all_facts = all_facts[:500]
elif len(all_facts) < 500:
    deficit = 500 - len(all_facts)
    print(f"Need {deficit} more facts, generating extras...")
    prompt = f"""Generate exactly {deficit} fascinating, surprising facts about world languages, writing systems, and linguistics. 
Each fact: 1-3 sentences. Must be genuinely interesting — "I want to tell someone this" level.
State positively (no negatives). Be accurate.
Return ONLY a JSON array of strings."""
    result = call_llm(prompt, max_tokens=6000)
    if result:
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            extras = json.loads(match.group())
            all_facts.extend(extras[:deficit])

# Deduplicate by first 40 chars lowercase
seen = set()
deduped = []
for f in all_facts:
    key = f.lower()[:40]
    if key not in seen:
        seen.add(key)
        deduped.append(f)
all_facts = deduped[:500]

print(f"Final count: {len(all_facts)}")

# Write
with open(OUTPUT, 'w', newline='') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['fact'])
    for fact in all_facts:
        writer.writerow([fact])

print(f"Written to {OUTPUT}")
