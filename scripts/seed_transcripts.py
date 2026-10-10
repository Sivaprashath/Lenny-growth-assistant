#!/usr/bin/env python3
"""
Seed script for Lenny Growth Assistant.
Indexes local transcripts from data/transcripts into ChromaDB vector store.
Can be run independently to test chunking, metadata extraction, and vector index generation.
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.services.knowledge_base import get_knowledge_base

configure_logging()
logger = get_logger("seed_transcripts")


def main():
    print("=" * 60)
    print("🎙️ Lenny Growth Assistant — Transcript Indexer")
    print("=" * 60)

    kb = get_knowledge_base()
    stats_before = kb.get_stats()
    print(f"📊 Current vector index: {stats_before['indexed_chunks']} chunks in {stats_before['vector_dir']}")

    print(f"📂 Reading transcripts from: {settings.TRANSCRIPTS_DIR}")
    count = kb.index_transcripts()
    print(f"✅ Successfully indexed {count} new document chunks!")

    stats_after = kb.get_stats()
    print(f"📊 Updated total: {stats_after['indexed_chunks']} indexed chunks")

    # Quick test retrieval
    test_queries = [
        "What is the North Star metric and retention curve?",
        "How did Airbnb find product-market fit with Brian Chesky?",
        "What is Elena Verna's framework for Product-Led Growth and viral loops?",
        "Explain Shreyas Doshi's LNO framework and High Agency",
    ]

    print("\n🔍 Running test semantic queries:")
    for query in test_queries:
        print(f"\n❓ Query: '{query}'")
        results = kb.retrieve(query, top_k=2)
        for i, res in enumerate(results, 1):
            print(f"   [{i}] Source: {res.citation} (score: {res.distance:.3f})")
            snippet = res.content[:140].replace("\n", " ") + "..."
            print(f"       \"{snippet}\"")

    print("\n" + "=" * 60)
    print("🎉 Ingestion and retrieval verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
