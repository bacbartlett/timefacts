#!/usr/bin/env python3
"""
Convert trivia Q&A pairs into single-sentence factoid statements using a cheap LLM via OpenRouter.
"""
import json
import urllib.request
import os
import time
import sys

INPUT = "/root/.openclaw/workspace/scrape-project/output/trivia.json"
OUTPUT = "/root/.openclaw/workspace/scrape-project/output/trivia_facts.json"
CHECKPOINT = "/root/.openclaw/workspace/scrape-project/output/trivia_facts_checkpoint.json"

# OpenRouter config
API_KEY = "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"
MODEL = "meta-llama/llama-3.2-3b-instruct"
BATCH_SIZE = 20  # Questions per API call
MAX_ITEMS = 10000  # Cap at 10K

def call_llm(prompt, max_tokens=2000):
    """Call OpenRouter API."""
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
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def build_batch_prompt(questions):
    """Build a prompt for a batch of questions."""
    lines = []
    for i, q in enumerate(questions):
        lines.append(f"{i+1}. Q: {q['question']} A: {q['correct_answer']}")
    
    return f"""Convert each trivia question+answer pair into a single factual statement. Output ONLY the numbered statements, one per line. Keep them concise (one sentence each). Do not add commentary.

{chr(10).join(lines)}"""

def parse_response(response, count):
    """Parse numbered statements from LLM response."""
    facts = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Remove numbering: "1. ", "1) ", etc.
        import re
        cleaned = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        if cleaned and len(cleaned) > 5:
            facts.append(cleaned)
    return facts

def main():
    if not API_KEY:
        print("ERROR: Set OPENROUTER_API_KEY environment variable")
        sys.exit(1)
    
    # Load trivia
    with open(INPUT) as f:
        trivia = json.load(f)
    
    trivia = trivia[:MAX_ITEMS]
    print(f"Processing {len(trivia)} trivia questions")
    
    # Load checkpoint if exists
    results = []
    start_idx = 0
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            results = json.load(f)
        start_idx = len(results)
        print(f"Resuming from checkpoint: {start_idx} already done")
    
    # Process in batches
    total = len(trivia)
    failed = 0
    
    for i in range(start_idx, total, BATCH_SIZE):
        batch = trivia[i:i+BATCH_SIZE]
        prompt = build_batch_prompt(batch)
        
        try:
            # Retry with backoff
            response = None
            for attempt in range(5):
                try:
                    response = call_llm(prompt)
                    break
                except Exception as retry_e:
                    if "429" in str(retry_e):
                        wait = 10 * (attempt + 1)
                        print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/5)")
                        time.sleep(wait)
                    else:
                        raise retry_e
            if response is None:
                raise Exception("Max retries exceeded")
            facts = parse_response(response, len(batch))
            
            # Match facts back to original questions
            for j, q in enumerate(batch):
                fact = facts[j] if j < len(facts) else f"{q['correct_answer']} is the answer to: {q['question']}"
                results.append({
                    "fact": fact,
                    "category": q.get("category", ""),
                    "original_question": q["question"],
                    "original_answer": q["correct_answer"],
                })
            
        except Exception as e:
            print(f"  Error at batch {i}: {e}")
            failed += 1
            # Fallback: simple concatenation
            for q in batch:
                results.append({
                    "fact": f"The answer to \"{q['question']}\" is {q['correct_answer']}.",
                    "category": q.get("category", ""),
                    "original_question": q["question"],
                    "original_answer": q["correct_answer"],
                })
            if failed > 10:
                print("Too many failures, saving checkpoint and stopping")
                break
            time.sleep(5)
        
        # Progress + checkpoint every 500
        if (i + BATCH_SIZE) % 500 < BATCH_SIZE:
            print(f"  Progress: {min(i+BATCH_SIZE, total)}/{total} ({len(results)} facts, {failed} errors)")
            with open(CHECKPOINT, "w") as f:
                json.dump(results, f, ensure_ascii=False)
        
        time.sleep(0.5)  # Paid tier, minimal rate limiting
    
    # Save final
    print(f"\n{'='*50}")
    print(f"Total facts generated: {len(results)}")
    print(f"Errors: {failed}")
    
    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Clean up checkpoint
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
    
    print(f"Saved to {OUTPUT}")

if __name__ == "__main__":
    main()
