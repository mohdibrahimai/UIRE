"""Synthetic dataset generator for UIRE.

Generates a JSONL file of random queries with domain labels to create
synthetic ambiguous queries for benchmarking.  Usage:

    python generate_synthetic.py 100 > uire_bench.jsonl

"""
import json
import random
import sys

DOMAINS = ["general", "finance", "medical", "legal", "travel", "education"]
QUERIES = [
    "Summarize this article",
    "Translate this paragraph",
    "Find me the best bank account",
    "Plan a trip",
    "Recommend a laptop",
    "Open an account quickly",
    "What's the fastest way to lose weight?",
    "Explain GDPR for me",
    "Give me a summary",
    "Best plan please",
]

def generate(n: int) -> None:
    rnd = random.Random(42)
    for _ in range(n):
        q = rnd.choice(QUERIES)
        dom = rnd.choice(DOMAINS)
        print(json.dumps({"query": q, "domain": dom}, ensure_ascii=False))

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    generate(n)
