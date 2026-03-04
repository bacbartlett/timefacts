#!/usr/bin/env python3
"""Add missing facts to language_500.csv to reach exactly 500."""
import csv
import json
import urllib.request
import re
import time

API_KEY = "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"
MODEL = "anthropic/claude-sonnet-4"
OUTPUT = "/root/.openclaw/workspace/scrape-project/output/language_500.csv"

def call_llm(prompt, max_tokens=4000):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8,
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
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

# Read existing
existing = []
with open(OUTPUT, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        existing.append(row['fact'])

need = 500 - len(existing)
print(f"Have {len(existing)}, need {need} more")

if need <= 0:
    print("Already have 500+")
    exit()

sample = "\n".join(f"- {f}" for f in existing[-15:])
prompt = f"""Generate exactly {need + 5} fascinating, surprising facts about world languages, writing systems, linguistics, and cross-language phenomena.

Each fact: 1-3 sentences. Must be genuinely interesting. State positively (no negatives). Be accurate.
Cover a MIX: some about lesser-known languages (Basque, Georgian, Navajo, Tagalog, etc.), some about writing quirks, some about linguistic oddities.

DO NOT repeat anything similar to these recent facts:
{sample}

Return ONLY a JSON array of strings."""

result = call_llm(prompt)
match = re.search(r'\[.*\]', result, re.DOTALL)
new_facts = json.loads(match.group())

# Dedup against existing
existing_keys = {f.lower()[:40] for f in existing}
unique_new = [f for f in new_facts if f.lower()[:40] not in existing_keys]

existing.extend(unique_new[:need])
print(f"Added {min(len(unique_new), need)}, total: {len(existing)}")

with open(OUTPUT, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['fact'])
    for fact in existing[:500]:
        writer.writerow([fact])

print(f"Written {min(len(existing), 500)} facts")
