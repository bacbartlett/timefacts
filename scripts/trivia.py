#!/usr/bin/env python3
"""Pull trivia questions from Open Trivia Database API."""
import json
import urllib.request
import time
import html

OUTPUT = "/root/.openclaw/workspace/scrape-project/output/trivia.json"

# First get category list
print("Fetching categories...")
resp = urllib.request.urlopen("https://opentdb.com/api_category.php")
categories = json.loads(resp.read())["trivia_categories"]
print(f"Found {len(categories)} categories")

# Get a session token
print("Getting session token...")
resp = urllib.request.urlopen("https://opentdb.com/api_token.php?command=request")
token = json.loads(resp.read())["token"]
print(f"Token: {token[:20]}...")

all_questions = []
seen = set()

# Pull 50 at a time from each category
for cat in categories:
    cat_id = cat["id"]
    cat_name = cat["name"]
    print(f"\nCategory: {cat_name} (id={cat_id})")
    
    for difficulty in ["easy", "medium", "hard"]:
        url = f"https://opentdb.com/api.php?amount=50&category={cat_id}&difficulty={difficulty}&token={token}"
        try:
            time.sleep(5.5)  # Rate limit: 1 req per 5 seconds
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            
            if data["response_code"] == 0:
                for q in data["results"]:
                    question = html.unescape(q["question"])
                    if question not in seen:
                        seen.add(question)
                        all_questions.append({
                            "question": question,
                            "correct_answer": html.unescape(q["correct_answer"]),
                            "incorrect_answers": [html.unescape(a) for a in q["incorrect_answers"]],
                            "category": html.unescape(q["category"]),
                            "difficulty": q["difficulty"],
                            "type": q["type"]
                        })
                print(f"  {difficulty}: +{len(data['results'])} (total: {len(all_questions)})")
            elif data["response_code"] == 4:
                print(f"  {difficulty}: exhausted")
            elif data["response_code"] == 1:
                print(f"  {difficulty}: not enough questions")
            else:
                print(f"  {difficulty}: response code {data['response_code']}")
        except Exception as e:
            print(f"  {difficulty}: error - {e}")

print(f"\n{'='*50}")
print(f"Total unique questions: {len(all_questions)}")

with open(OUTPUT, "w") as f:
    json.dump(all_questions, f, indent=2, ensure_ascii=False)

print(f"Saved to {OUTPUT}")
