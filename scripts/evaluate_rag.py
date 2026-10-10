#!/usr/bin/env python3
"""
RAG Evaluation Script for Lenny Growth Assistant.
Tests precision and ground truth source matching for standard growth & product strategy queries.
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.knowledge_base import get_knowledge_base

EVAL_BENCHMARKS = [
    {
        "query": "How did Airbnb get their first hosts and what is the 11-star experience?",
        "expected_guest": "Brian Chesky",
        "expected_keywords": ["11-star", "Paul Graham", "photos"],
    },
    {
        "query": "What are the three product virality loops in B2B SaaS?",
        "expected_guest": "Elena Verna",
        "expected_keywords": ["virality", "loop", "collaboration"],
    },
    {
        "query": "How do you apply the LNO framework to PM time management?",
        "expected_guest": "Shreyas Doshi",
        "expected_keywords": ["leverage", "neutral", "overhead"],
    },
    {
        "query": "Why are growth loops better than traditional marketing funnels?",
        "expected_guest": "Casey Winters",
        "expected_keywords": ["closed system", "compounding", "cac"],
    },
    {
        "query": "What is the 5-part positioning framework?",
        "expected_guest": "April Dunford",
        "expected_keywords": ["context", "alternatives", "category"],
    },
    {
        "query": "Why is retention the only metric that matters at YC?",
        "expected_guest": "Gustaf Alstromer",
        "expected_keywords": ["cohort", "flat tail", "north star"],
    },
]


def run_eval():
    kb = get_knowledge_base()
    stats = kb.get_stats()
    print(f"🔬 Evaluating RAG Retrieval Quality ({stats['indexed_chunks']} chunks in DB)...")
    print("-" * 70)

    passed = 0
    total = len(EVAL_BENCHMARKS)

    for i, test in enumerate(EVAL_BENCHMARKS, 1):
        query = test["query"]
        expected_guest = test["expected_guest"]
        results = kb.retrieve(query, top_k=3)

        if not results:
            print(f"❌ Test {i}: '{query[:40]}...' -> No results returned")
            continue

        top_match = results[0]
        guest_matched = expected_guest.lower() in (top_match.guest or "").lower() or expected_guest.lower() in top_match.content.lower()

        # Check keyword presence
        combined_text = " ".join(r.content for r in results).lower()
        keywords_found = [kw for kw in test["expected_keywords"] if kw.lower() in combined_text]
        keyword_pct = len(keywords_found) / len(test["expected_keywords"])

        if guest_matched and keyword_pct >= 0.5:
            passed += 1
            status = "✅ PASS"
        else:
            status = "⚠️ PARTIAL" if guest_matched else "❌ FAIL"

        print(f"{status} [{i}/{total}] Query: '{query[:45]}...'")
        print(f"    Expected: {expected_guest} | Top Source: {top_match.citation} (dist: {top_match.distance:.3f})")
        print(f"    Keywords matched: {keywords_found}/{test['expected_keywords']}")
        print()

    print("-" * 70)
    score_pct = (passed / total) * 100
    print(f"🎯 Evaluation Complete: {passed}/{total} Passed ({score_pct:.1f}% Precision@Top3)")
    return passed == total


if __name__ == "__main__":
    run_eval()
