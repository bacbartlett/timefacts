#!/usr/bin/env python3
"""
Build 4 x 500-item CSV files for e-ink clock display.
1. trivia_500.csv - filtered from existing 10K
2. history_500.csv - generated timeless history facts
3. language_500.csv - generated language facts
4. quotes_500.csv - filtered from existing 2555
"""
import json
import urllib.request
import csv
import os
import time
import sys
import random

API_KEY = "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"
MODEL_FILTER = "anthropic/claude-sonnet-4" # better judgment for filtering
MODEL_GEN = "anthropic/claude-sonnet-4"
OUTPUT_DIR = "/root/.openclaw/workspace/scrape-project/output"

def call_llm(prompt, model=MODEL_FILTER, max_tokens=4000, temperature=0.3):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return ""

def write_facts_csv(filepath, facts, col="fact"):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([col])
        for fact in facts:
            w.writerow([fact.strip()])
    print(f"  Wrote {len(facts)} items to {filepath}")

def write_quotes_csv(filepath, quotes):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["quote", "author"])
        for q, a in quotes:
            w.writerow([q.strip(), a.strip()])
    print(f"  Wrote {len(quotes)} items to {filepath}")

# ============================================================
# TASK 1: Filter trivia facts
# ============================================================
def filter_trivia():
    print("=== TASK 1: Filtering trivia facts ===")
    checkpoint = os.path.join(OUTPUT_DIR, "trivia_filter_checkpoint.json")
    
    if os.path.exists(checkpoint):
        with open(checkpoint) as f:
            kept = json.load(f)
        print(f"  Loaded {len(kept)} from checkpoint")
        if len(kept) >= 500:
            write_facts_csv(os.path.join(OUTPUT_DIR, "trivia_500.csv"), kept[:500])
            return kept[:500]
    else:
        kept = []
    
    # Read existing facts
    facts = []
    with open(os.path.join(OUTPUT_DIR, "trivia_facts.csv"), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fact = row.get("fact", "").strip()
            if fact and len(fact) > 15 and len(fact) < 300:
                facts.append(fact)
    
    print(f"  Read {len(facts)} candidate facts")
    random.seed(42)
    random.shuffle(facts)
    
    # Process in batches
    batch_size = 100
    already_processed = len(kept) * 3  # rough estimate of how many we've seen
    start_idx = min(already_processed, len(facts))
    
    for i in range(0, len(facts), batch_size):
        if len(kept) >= 600:
            break
        batch = facts[i:i+batch_size]
        numbered = "\n".join(f"{j+1}. {f}" for j, f in enumerate(batch))
        
        prompt = f"""You're curating facts for an e-ink clock display. A college student glances up and reads one fact. It should make them go "huh, interesting!" or want to tell someone.

Rate each fact below. Return ONLY the numbers of facts worth keeping (the genuinely surprising, delightful, "I didn't know that!" ones).

KILL: boring, obvious ("water is wet"), too niche, negative framing, trivia only a specialist cares about, things everyone already knows
KEEP: surprising, delightful, makes you want to share, "wait really??" factor

Facts:
{numbered}

Return a JSON array of the numbers to KEEP, like [1, 5, 12, ...]. Nothing else."""

        result = call_llm(prompt, max_tokens=2000)
        try:
            # Extract JSON array from response
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                nums = json.loads(result[start:end])
                for n in nums:
                    if 1 <= n <= len(batch):
                        kept.append(batch[n-1])
        except Exception as e:
            print(f"  Parse error: {e}")
        
        print(f"  Processed batch {i//batch_size + 1}, kept so far: {len(kept)}")
        
        # Checkpoint every 5 batches
        if (i // batch_size) % 5 == 4:
            with open(checkpoint, "w") as f:
                json.dump(kept, f)
    
    with open(checkpoint, "w") as f:
        json.dump(kept, f)
    
    final = kept[:500]
    write_facts_csv(os.path.join(OUTPUT_DIR, "trivia_500.csv"), final)
    return final

# ============================================================
# TASK 2: Generate history facts
# ============================================================
def generate_history():
    print("=== TASK 2: Generating history facts ===")
    checkpoint = os.path.join(OUTPUT_DIR, "history_gen_checkpoint.json")
    
    if os.path.exists(checkpoint):
        with open(checkpoint) as f:
            facts = json.load(f)
        print(f"  Loaded {len(facts)} from checkpoint")
        if len(facts) >= 500:
            write_facts_csv(os.path.join(OUTPUT_DIR, "history_500.csv"), facts[:500])
            return facts[:500]
    else:
        facts = []
    
    topics = [
        "ancient civilizations (Egypt, Rome, Greece, Mesopotamia, China, India, Maya, Aztec)",
        "medieval history worldwide (Europe, Islamic Golden Age, Tang Dynasty, Vikings, Mongols)",
        "age of exploration and colonialism",
        "scientific and medical history breakthroughs",
        "wars and conflicts — surprising facts, not just dates",
        "historical figures — unexpected personal details",
        "everyday life in past centuries — food, hygiene, customs",
        "industrial revolution and modern era",
        "cold war, space race, 20th century",
        "African, South American, and Asian history often overlooked in Western education",
    ]
    
    per_batch = 55
    for topic in topics:
        if len(facts) >= 550:
            break
        prompt = f"""Generate {per_batch} fascinating, TIMELESS history facts about: {topic}

These are for an e-ink clock display. A student glances up and reads one. It should make them go "Wait, really??" or want to tell someone.

Rules:
- 1-2 sentences each, max 3
- State things in the positive (what IS true)
- NOT tied to specific dates like "On this day in..." — these are timeless
- Surprising, counterintuitive, or little-known
- Factually accurate — don't make things up
- Mix of cultures and regions
- Examples of the vibe: "Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid." / "Oxford University is older than the Aztec Empire."

Return as a JSON array of strings. Nothing else."""

        result = call_llm(prompt, model=MODEL_GEN, max_tokens=4000, temperature=0.7)
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                batch = json.loads(result[start:end])
                facts.extend([f for f in batch if isinstance(f, str) and len(f) > 15])
                print(f"  Topic '{topic[:40]}': got {len(batch)}, total {len(facts)}")
        except Exception as e:
            print(f"  Parse error for topic '{topic[:30]}': {e}")
        
        with open(checkpoint, "w") as f:
            json.dump(facts, f)
    
    # Deduplicate
    seen = set()
    unique = []
    for f in facts:
        key = f.lower().strip()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(f)
    facts = unique
    
    final = facts[:500]
    write_facts_csv(os.path.join(OUTPUT_DIR, "history_500.csv"), final)
    return final

# ============================================================
# TASK 3: Generate language facts
# ============================================================
def generate_language():
    print("=== TASK 3: Generating language facts ===")
    checkpoint = os.path.join(OUTPUT_DIR, "language_gen_checkpoint.json")
    
    if os.path.exists(checkpoint):
        with open(checkpoint) as f:
            facts = json.load(f)
        print(f"  Loaded {len(facts)} from checkpoint")
        if len(facts) >= 500:
            write_facts_csv(os.path.join(OUTPUT_DIR, "language_500.csv"), facts[:500])
            return facts[:500]
    else:
        facts = []
    
    topics = [
        "etymology — surprising word origins in English",
        "alphabets and writing systems around the world",
        "linguistic quirks — palindromes, pangrams, unusual grammar rules",
        "endangered and unusual languages",
        "how languages change over time — sound shifts, borrowed words",
        "names for things you didn't know had names (semantic gaps, specific terms)",
        "sign languages, braille, and non-spoken communication",
        "multilingualism, translation oddities, untranslatable words",
        "numbers, counting systems, and mathematical language",
        "place names, personal names, and naming conventions worldwide",
    ]
    
    per_batch = 55
    for topic in topics:
        if len(facts) >= 550:
            break
        prompt = f"""Generate {per_batch} fascinating facts about: {topic}

These are for an e-ink clock display. A student glances up and reads one fact about language/linguistics. It should make them go "Huh, cool!" or want to tell someone.

Rules:
- 1-2 sentences each, max 3
- State things in the positive (what IS true)
- Surprising, delightful, or little-known
- Factually accurate
- Examples: "Hawaiian has only 13 letters in its alphabet." / "The dot over 'i' and 'j' is called a tittle." / "The word 'mortgage' comes from French for 'death pledge.'"

Return as a JSON array of strings. Nothing else."""

        result = call_llm(prompt, model=MODEL_GEN, max_tokens=4000, temperature=0.7)
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                batch = json.loads(result[start:end])
                facts.extend([f for f in batch if isinstance(f, str) and len(f) > 15])
                print(f"  Topic '{topic[:40]}': got {len(batch)}, total {len(facts)}")
        except Exception as e:
            print(f"  Parse error for topic '{topic[:30]}': {e}")
        
        with open(checkpoint, "w") as f:
            json.dump(facts, f)
    
    seen = set()
    unique = []
    for f in facts:
        key = f.lower().strip()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(f)
    facts = unique
    
    final = facts[:500]
    write_facts_csv(os.path.join(OUTPUT_DIR, "language_500.csv"), final)
    return final

# ============================================================
# TASK 4: Filter inspirational quotes
# ============================================================
def filter_quotes():
    print("=== TASK 4: Filtering inspirational quotes ===")
    checkpoint = os.path.join(OUTPUT_DIR, "quotes_filter_checkpoint.json")
    
    if os.path.exists(checkpoint):
        with open(checkpoint) as f:
            kept = json.load(f)
        print(f"  Loaded {len(kept)} from checkpoint")
        if len(kept) >= 500:
            write_quotes_csv(os.path.join(OUTPUT_DIR, "quotes_500.csv"), kept[:500])
            return kept[:500]
    else:
        kept = []
    
    quotes = []
    with open(os.path.join(OUTPUT_DIR, "inspirational_quotes.csv"), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row.get("quote", "").strip()
            a = row.get("author", "").strip()
            if q and len(q) > 10 and len(q) < 300:
                quotes.append((q, a))
    
    print(f"  Read {len(quotes)} candidate quotes")
    
    batch_size = 80
    for i in range(0, len(quotes), batch_size):
        if len(kept) >= 550:
            break
        batch = quotes[i:i+batch_size]
        numbered = "\n".join(f'{j+1}. "{q}" — {a}' for j, (q, a) in enumerate(batch))
        
        prompt = f"""You're curating quotes for an e-ink clock display. A college student glances up and reads one. It should make them pause, think, or feel genuinely motivated.

Rate each quote below. Return ONLY the numbers worth keeping.

KILL: generic platitudes ("believe in yourself"), vapid positivity, quotes that are just... fine, overly long, unclear without context
KEEP: makes you pause and think, genuinely wise, elegant phrasing, timeless insight, the kind you'd screenshot and send to a friend

Quotes:
{numbered}

Return a JSON array of the numbers to KEEP, like [1, 5, 12, ...]. Nothing else."""

        result = call_llm(prompt, max_tokens=2000)
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                nums = json.loads(result[start:end])
                for n in nums:
                    if 1 <= n <= len(batch):
                        kept.append(list(batch[n-1]))
        except Exception as e:
            print(f"  Parse error: {e}")
        
        print(f"  Processed batch {i//batch_size + 1}, kept so far: {len(kept)}")
        
        if (i // batch_size) % 5 == 4:
            with open(checkpoint, "w") as f:
                json.dump(kept, f)
    
    with open(checkpoint, "w") as f:
        json.dump(kept, f)
    
    # Supplement if needed
    if len(kept) < 500:
        needed = 500 - len(kept)
        print(f"  Need {needed} more quotes, generating supplements...")
        prompt = f"""Generate {needed} genuinely inspirational quotes with their authors. Mix of well-known and lesser-known thinkers, writers, leaders, scientists, artists.

These go on an e-ink clock display. Quality bar: makes a college student pause mid-homework and think.

NO generic platitudes. YES to genuine wisdom, elegant insight, surprising perspective.

Return as a JSON array of objects with "quote" and "author" keys. Nothing else."""
        
        result = call_llm(prompt, model=MODEL_GEN, max_tokens=4000, temperature=0.7)
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                extras = json.loads(result[start:end])
                for item in extras:
                    if isinstance(item, dict):
                        kept.append([item.get("quote",""), item.get("author","")])
        except Exception as e:
            print(f"  Supplement parse error: {e}")
    
    final = kept[:500]
    write_quotes_csv(os.path.join(OUTPUT_DIR, "quotes_500.csv"), final)
    return final

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if task in ("trivia", "all"):
        filter_trivia()
    if task in ("history", "all"):
        generate_history()
    if task in ("language", "all"):
        generate_language()
    if task in ("quotes", "all"):
        filter_quotes()
    
    print("\n=== DONE ===")
