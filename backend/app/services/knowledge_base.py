"""
RAG (Retrieval-Augmented Generation) Service.
Manages transcript ingestion, chunking, vector indexing, and semantic retrieval
using ChromaDB as the local vector store with sentence-transformers embeddings.
"""
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved transcript chunk with source metadata."""
    content: str
    source_file: str
    episode_title: str
    episode_number: Optional[str]
    guest: Optional[str]
    distance: float
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        parts = []
        if self.episode_number:
            parts.append(f"Episode {self.episode_number}")
        if self.episode_title:
            parts.append(f'"{self.episode_title}"')
        if self.guest:
            parts.append(f"with {self.guest}")
        return " – ".join(parts) if parts else self.source_file


class TranscriptIngester:
    """Loads, cleans, and chunks podcast transcripts from the local directory."""

    SPEAKER_PATTERN = re.compile(r'^[A-Z][A-Za-z\s]+:\s*', re.MULTILINE)

    def __init__(self, transcripts_dir: str, chunk_size: int, chunk_overlap: int):
        self.transcripts_dir = Path(transcripts_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _parse_metadata(self, filepath: Path) -> dict:
        """Extract episode metadata from filename or frontmatter."""
        stem = filepath.stem
        # Pattern: "123-episode-title" or "episode-123-title"
        num_match = re.match(r'^(\d+)[-_](.+)', stem)
        if num_match:
            ep_num = num_match.group(1)
            title_raw = num_match.group(2).replace("-", " ").replace("_", " ").title()
        else:
            ep_num = None
            title_raw = stem.replace("-", " ").replace("_", " ").title()

        return {
            "episode_number": ep_num,
            "episode_title": title_raw,
            "source_file": filepath.name,
            "guest": None,  # Could be extracted from content in v2
        }

    def _chunk_text(self, text: str) -> list[str]:
        """Sliding window chunking preserving speaker context."""
        words = text.split()
        chunks = []
        start = 0
        chunk_words = self.chunk_size // 4  # approx words per chunk_size chars
        overlap_words = self.chunk_overlap // 4

        while start < len(words):
            end = start + chunk_words
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - overlap_words
            if start >= len(words):
                break

        return [c for c in chunks if len(c.strip()) > 100]

    def ingest(self) -> list[dict]:
        """
        Load all .txt / .md transcript files and return chunked documents.
        Each document includes text + metadata for embedding.
        """
        if not self.transcripts_dir.exists():
            logger.warning("transcripts_dir_missing", path=str(self.transcripts_dir))
            return self._load_sample_transcripts()

        documents = []
        files = list(self.transcripts_dir.glob("**/*.txt")) + \
                list(self.transcripts_dir.glob("**/*.md"))

        if not files:
            logger.warning("no_transcript_files_found", path=str(self.transcripts_dir))
            return self._load_sample_transcripts()

        for filepath in files:
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
                meta = self._parse_metadata(filepath)
                chunks = self._chunk_text(text)

                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{filepath.name}:{i}".encode()).hexdigest()
                    documents.append({
                        "id": doc_id,
                        "text": chunk,
                        "chunk_index": i,
                        **meta,
                    })

                logger.info("transcript_ingested", file=filepath.name, chunks=len(chunks))
            except Exception as e:
                logger.error("transcript_ingest_error", file=str(filepath), error=str(e))

        logger.info("ingestion_complete", total_documents=len(documents))
        return documents

    def _load_sample_transcripts(self) -> list[dict]:
        """
        Fallback: built-in sample excerpts from Lenny's Podcast for demo purposes.
        These are paraphrased public summaries — not verbatim transcripts.
        """
        samples = [
            {
                "id": "sample-001-0",
                "text": (
                    "Lenny Rachitsky: Brian Chesky, what's the secret to building a product people love? "
                    "Brian Chesky: You have to think like a designer. When we launched Airbnb, we went "
                    "door to door taking photos of listings ourselves. The idea was to make the experience "
                    "11-star — what would it look like if we far exceeded every expectation? Not just 5-star. "
                    "Go beyond what users ask for. That obsessive focus on the customer journey is what "
                    "separated us from every other marketplace. Product-market fit isn't found in surveys. "
                    "It's found by watching how customers actually use your product."
                ),
                "episode_number": "1",
                "episode_title": "How Airbnb Found Product-Market Fit with Brian Chesky",
                "source_file": "sample_chesky.txt",
                "guest": "Brian Chesky",
                "chunk_index": 0,
            },
            {
                "id": "sample-001-1",
                "text": (
                    "Lenny: How do you think about growth at Airbnb early on? "
                    "Brian Chesky: Growth comes from retention, not acquisition. If you get retention right, "
                    "growth is a side effect. We focused obsessively on the first trip experience. "
                    "Make the first trip so magical that guests come back and tell their friends. "
                    "The growth loop we built was: guest has amazing experience → tells friends → "
                    "friends become hosts or guests → compounding network effects. "
                    "Word of mouth is the most powerful growth channel. It's free, scalable, and "
                    "produces the highest-quality customers."
                ),
                "episode_number": "1",
                "episode_title": "How Airbnb Found Product-Market Fit with Brian Chesky",
                "source_file": "sample_chesky.txt",
                "guest": "Brian Chesky",
                "chunk_index": 1,
            },
            {
                "id": "sample-002-0",
                "text": (
                    "Lenny Rachitsky: What is the North Star metric and why does it matter? "
                    "Shaun Clowes: The North Star metric is the single number that best captures "
                    "the core value your product delivers to customers. For Spotify, it might be "
                    "listening hours. For Airbnb, it's nights booked. The danger is picking a "
                    "vanity metric like signups. You want to find the metric that, when it grows, "
                    "genuinely means your customers are getting more value. Everything your team "
                    "does should ladder up to moving that one number."
                ),
                "episode_number": "2",
                "episode_title": "The North Star Framework",
                "source_file": "sample_north_star.txt",
                "guest": "Shaun Clowes",
                "chunk_index": 0,
            },
            {
                "id": "sample-003-0",
                "text": (
                    "Lenny: How should early-stage startups think about pricing? "
                    "Patrick Campbell: Most founders leave money on the table because they set prices "
                    "based on gut feeling or competitor copying. Value-based pricing is the answer. "
                    "Ask customers: what would make this too expensive? What would make you think it's "
                    "cheap enough to not be worth trying? That Van Westendorp model gives you a "
                    "price range that the market will accept. Your price is a signal of quality. "
                    "Underpricing can actually kill conversion because buyers assume low quality."
                ),
                "episode_number": "3",
                "episode_title": "Pricing Strategies for Growth",
                "source_file": "sample_pricing.txt",
                "guest": "Patrick Campbell",
                "chunk_index": 0,
            },
            {
                "id": "sample-004-0",
                "text": (
                    "Lenny: What separates great PMs from good ones? "
                    "Shreyas Doshi: Great PMs are ruthlessly focused on outcomes, not outputs. "
                    "They understand that shipping features is easy. Delivering business and user "
                    "outcomes is hard. The best PMs I've seen can hold two things simultaneously: "
                    "a deep empathy for users and a sharp business model understanding. They ask "
                    "'what problem are we solving?' before 'what should we build?'. They also "
                    "know when NOT to build — which is the most underrated PM skill."
                ),
                "episode_number": "4",
                "episode_title": "What Great Product Management Looks Like",
                "source_file": "sample_pm_skills.txt",
                "guest": "Shreyas Doshi",
                "chunk_index": 0,
            },
            {
                "id": "sample-004-1",
                "text": (
                    "Shreyas Doshi: The concept of 'DRI' — directly responsible individual — is "
                    "critical for product teams. Each initiative needs one person accountable, not "
                    "a committee. When everyone is responsible, no one is. Great PMs also master "
                    "stakeholder management — they know how to bring engineering, design, marketing, "
                    "and leadership along on the journey rather than dropping decisions from above. "
                    "Influence without authority is the core PM superpower."
                ),
                "episode_number": "4",
                "episode_title": "What Great Product Management Looks Like",
                "source_file": "sample_pm_skills.txt",
                "guest": "Shreyas Doshi",
                "chunk_index": 1,
            },
            {
                "id": "sample-005-0",
                "text": (
                    "Lenny: How do you know when you've found product-market fit? "
                    "Elena Verna: The Sean Ellis test is a good starting point — ask users 'How "
                    "would you feel if you could no longer use this product?' If 40%+ say 'very "
                    "disappointed', you likely have PMF. But qualitative signals matter more in "
                    "early stages. Is your churn negligible? Do users come back without prompting? "
                    "Do they refer others unprompted? Are sales cycles getting shorter, not longer? "
                    "PMF is felt before it's measured — your team stops constantly fighting to "
                    "retain users and starts feeling a pull from the market."
                ),
                "episode_number": "5",
                "episode_title": "How to Find Product-Market Fit",
                "source_file": "sample_pmf.txt",
                "guest": "Elena Verna",
                "chunk_index": 0,
            },
        ]
        logger.info("using_sample_transcripts", count=len(samples))
        return samples


class KnowledgeBaseService:
    """
    Manages the ChromaDB vector store for transcript retrieval.
    Handles ingestion, embedding, and semantic search.
    """

    def __init__(self):
        self._collection = None
        self._ingester = TranscriptIngester(
            transcripts_dir=settings.TRANSCRIPTS_DIR,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    def _get_collection(self):
        """Lazy-load ChromaDB collection."""
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self._collection = client.get_or_create_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except ImportError:
            raise RuntimeError(
                "chromadb not installed. Run: pip install chromadb sentence-transformers"
            )

    def index_transcripts(self, force_reindex: bool = False) -> int:
        """
        Ingest transcripts and index into ChromaDB.
        Skips already-indexed documents unless force_reindex=True.
        Returns number of new documents indexed.
        """
        collection = self._get_collection()
        existing_count = collection.count()

        if existing_count > 0 and not force_reindex:
            logger.info("knowledge_base_already_indexed", count=existing_count)
            return 0

        documents = self._ingester.ingest()
        if not documents:
            logger.warning("no_documents_to_index")
            return 0

        # Batch upsert
        batch_size = 100
        indexed = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            collection.upsert(
                ids=[d["id"] for d in batch],
                documents=[d["text"] for d in batch],
                metadatas=[{
                    k: v for k, v in d.items()
                    if k not in ("id", "text") and v is not None
                } for d in batch],
            )
            indexed += len(batch)

        logger.info("knowledge_base_indexed", total=indexed)
        return indexed

    def retrieve(self, query: str, top_k: int = None) -> list[RetrievedChunk]:
        """
        Semantic retrieval: find the top-k most relevant transcript chunks.
        Returns structured RetrievedChunk objects with citation metadata.
        """
        collection = self._get_collection()
        k = top_k or settings.TOP_K_RETRIEVAL

        try:
            results = collection.query(
                query_texts=[query],
                n_results=min(k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("retrieval_error", query=query[:100], error=str(e))
            return []

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0=identical, 2=opposite
            # Filter by similarity threshold (convert distance to similarity)
            similarity = 1 - (dist / 2)
            if similarity < settings.SIMILARITY_THRESHOLD:
                continue

            chunks.append(RetrievedChunk(
                content=doc,
                source_file=meta.get("source_file", "unknown"),
                episode_title=meta.get("episode_title", ""),
                episode_number=meta.get("episode_number"),
                guest=meta.get("guest"),
                distance=dist,
                chunk_index=meta.get("chunk_index", 0),
                metadata=meta,
            ))

        logger.info("retrieval_complete", query=query[:60], results=len(chunks))
        return chunks

    def get_stats(self) -> dict:
        """Return knowledge base statistics for the health endpoint."""
        try:
            collection = self._get_collection()
            return {
                "total_chunks": collection.count(),
                "collection_name": settings.COLLECTION_NAME,
                "persist_dir": settings.CHROMA_PERSIST_DIR,
                "status": "ready",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton
_kb_service: Optional[KnowledgeBaseService] = None


def get_knowledge_base() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService()
    return _kb_service
