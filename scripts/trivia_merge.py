#!/usr/bin/env python3
"""Parse OpenTriviaQA files and merge with OpenTDB data."""
import json
import os
import re

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/trivia.json"
QA_DIR = "/root/.openclaw/workspace/scrape-project/OpenTriviaQA/categories"

# Load existing OpenTDB data
with open(OUTPUT) as f:
    existing = json.load(f)

print(f"Existing OpenTDB questions: {len(existing)}")
seen = set(q["question"] for q in existing)
all_questions = list(existing)

# Parse OpenTriviaQA format
for filename in sorted(os.listdir(QA_DIR)):
    filepath = os.path.join(QA_DIR, filename)
    category = filename.replace("-", " ").title()
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Parse: #Q question\n^ correct\nA wrong1\nB wrong2...
    blocks = content.split("#Q ")
    count = 0
    for block in blocks[1:]:  # skip first empty
        lines = block.strip().split("\n")
        if not lines:
            continue
        
        question = lines[0].strip()
        correct = ""
        incorrect = []
        
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("^ "):
                correct = line[2:].strip()
            elif re.match(r'^[A-Z] ', line):
                incorrect.append(line[2:].strip())
        
        if question and correct and question not in seen:
            seen.add(question)
            all_questions.append({
                "question": question,
                "correct_answer": correct,
                "incorrect_answers": incorrect,
                "category": category,
                "difficulty": "medium",
                "type": "multiple" if incorrect else "boolean",
                "source": "OpenTriviaQA"
            })
            count += 1
    
    print(f"  {category}: +{count} (total: {len(all_questions)})")

print(f"\nTotal unique questions: {len(all_questions)}")

with open(OUTPUT, "w") as f:
    json.dump(all_questions, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
