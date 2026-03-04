#!/usr/bin/env python3
"""Re-filter trivia_facts.csv to 500 genuinely interesting facts using LLM scoring."""
import csv
import json
import urllib.request
import re
import time
import sys

API_KEY = "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"
MODEL = "anthropic/claude-sonnet-4"
INPUT = "/root/.openclaw/workspace/scrape-project/output/trivia_facts.csv"
OUTPUT = "/root/.openclaw/workspace/scrape-project/output/trivia_500.csv"
CHECKPOINT = "/root/.openclaw/workspace/scrape-project/output/trivia_refilter_checkpoint.json"

def call_llm(prompt, max_tokens=4000):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
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

def prefilter(fact):
    """Quick rule-based cuts before LLM scoring."""
    f = fact.lower().strip()
    # Too short or too long
    if len(f) < 20 or len(f) > 300:
        return False
    # Negatives
    if re.search(r'\b(does not|is not|isn\'t|doesn\'t|cannot|can\'t|did not|didn\'t|was not|wasn\'t|are not|aren\'t|were not|weren\'t)\b', f):
        return False
    # Celebrity height/weight
    if re.search(r'\d+\s*(feet|foot|inches|inch|lbs|pounds|kg|cm)\b', f):
        return False
    # Boring patterns
    if re.search(r'(is (also )?known (as|for)|was born (in|on)|real name|birth name|middle name)', f):
        return False
    # "X is from Y" or "X is located in Y" (too simple)
    if re.match(r'^[^.]+\bis (from|located in|native to|found in)\b', f) and len(f) < 60:
        return False
    # Video game specifics nobody cares about
    if re.search(r'(player class|appeared in .* vs|team fortress|fortnite|overwatch|call of duty|minecraft)', f):
        return False
    # "X dislikes/likes Y" celebrity opinions
    if re.search(r'(dislikes|likes|hates|loves|prefers|favorite)\b.*\b(movie|film|song|book)', f):
        return False
    # "The lyrics..." or "The following lyrics"
    if 'lyrics' in f:
        return False
    # "X is false/true" pattern from bad Q&A conversion
    if f.endswith('false.') or f.endswith('true.'):
        return False
    # Acrophobia-style definitions that are obvious
    if re.search(r'phobia means fear of', f):
        return False
    return True

# Load all facts
print("Loading facts...")
facts = []
with open(INPUT, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        facts.append(row['fact'].strip().strip('"'))

print(f"Total facts: {len(facts)}")

# Pre-filter
filtered = [f for f in facts if prefilter(f)]
print(f"After pre-filter: {len(filtered)}")

# Remove duplicates (case-insensitive first 50 chars)
seen = set()
deduped = []
for f in filtered:
    key = f.lower()[:50]
    if key not in seen:
        seen.add(key)
        deduped.append(f)
filtered = deduped
print(f"After dedup: {len(filtered)}")

# Load checkpoint
scored = []
start_batch = 0
try:
    with open(CHECKPOINT, 'r') as f:
        scored = json.load(f)
    start_batch = len(scored)
    print(f"Resuming from checkpoint: {start_batch} batches done")
except:
    pass

# Score in batches of 50 via LLM
BATCH_SIZE = 50
batches = [filtered[i:i+BATCH_SIZE] for i in range(0, len(filtered), BATCH_SIZE)]
print(f"Total batches: {len(batches)}")

for i, batch in enumerate(batches):
    if i < start_batch:
        continue
    print(f"Batch {i+1}/{len(batches)}...")
    
    numbered = "\n".join(f"{j+1}. {fact}" for j, fact in enumerate(batch))
    prompt = f"""Rate each fact 1-10 for "wow factor" — would a college student glance at this on a clock display and think "oh that's cool" or want to tell someone?

10 = mind-blowing, must share
7-9 = genuinely surprising/delightful  
4-6 = mildly interesting
1-3 = boring, obvious, or "so what?"

INSTANT 1: celebrity trivia nobody cares about, niche sports stats, video game details, obvious common knowledge, anything where the reaction is "ok... and?"

Return ONLY a JSON array of scores, one per fact. Example: [3, 8, 2, 7, ...]

Facts:
{numbered}"""

    result = call_llm(prompt)
    if result is None:
        print(f"  Failed batch {i+1}, skipping")
        scored.append([3] * len(batch))  # default low
        continue
    
    # Parse scores
    try:
        # Find JSON array in response
        match = re.search(r'\[[\d\s,]+\]', result)
        if match:
            scores = json.loads(match.group())
        else:
            print(f"  No JSON array found, defaulting to 3s")
            scores = [3] * len(batch)
    except:
        print(f"  Parse error, defaulting to 3s")
        scores = [3] * len(batch)
    
    # Pad/trim to match batch size
    while len(scores) < len(batch):
        scores.append(3)
    scores = scores[:len(batch)]
    
    scored.append(scores)
    
    # Checkpoint every 5 batches
    if (i + 1) % 5 == 0:
        with open(CHECKPOINT, 'w') as f:
            json.dump(scored, f)
        print(f"  Checkpointed at batch {i+1}")
    
    time.sleep(0.5)

# Save final checkpoint
with open(CHECKPOINT, 'w') as f:
    json.dump(scored, f)

# Flatten scores and pair with facts
all_scores = []
for batch_scores in scored:
    all_scores.extend(batch_scores)

# Pair and sort
pairs = list(zip(filtered[:len(all_scores)], all_scores[:len(filtered)]))
pairs.sort(key=lambda x: x[1], reverse=True)

print(f"\nScore distribution:")
for s in range(10, 0, -1):
    count = sum(1 for _, score in pairs if score == s)
    print(f"  {s}: {count}")

# Take top 500
top500 = [fact for fact, score in pairs[:500]]
print(f"\nSelected {len(top500)} facts (min score: {pairs[499][1] if len(pairs) >= 500 else 'N/A'})")

# Write output
with open(OUTPUT, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['fact'])
    for fact in top500:
        writer.writerow([fact])

print(f"Written to {OUTPUT}")
