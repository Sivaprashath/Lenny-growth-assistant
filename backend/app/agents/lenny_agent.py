"""
Agent Layer — routing and execution of specialized skills.
Handles:
  1. Grounded RAG Q&A (default)
  2. Ship 30 for 30 essay generation
  3. Artifact (Markdown/HTML) generation
"""
import json
import re
import time
from dataclasses import dataclass
from typing import Optional, AsyncGenerator
from enum import Enum

from app.core.llm_client import BaseLLMClient, LLMMessage
from app.services.knowledge_base import KnowledgeBaseService, RetrievedChunk
from app.skills.ship_30 import SHIP_30_SYSTEM_PROMPT, SHIP_30_USER_TEMPLATE
from app.skills.artifact_gen import ARTIFACT_SYSTEM_PROMPT, build_artifact_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)


class SkillType(str, Enum):
    RAG_QA = "rag_qa"
    SHIP_30_ESSAY = "ship_30_essay"
    ARTIFACT_MARKDOWN = "artifact_markdown"
    ARTIFACT_HTML = "artifact_html"


@dataclass
class AgentResponse:
    content: str
    skill_used: SkillType
    sources: list[dict]
    retrieval_score: Optional[float]
    latency_ms: float
    artifact_type: Optional[str] = None  # "markdown" | "html" | None


# ── Intent Router ──────────────────────────────────────────────────────────────

SHIP_30_TRIGGERS = re.compile(
    r'\b(ship 30|ship30|essay|long.?form|written piece|newsletter|atomic essay|'
    r'write (a|an|me) (post|article|essay|piece)|draft)\b',
    re.IGNORECASE
)

ARTIFACT_MD_TRIGGERS = re.compile(
    r'\b(markdown|\.md|document|structured doc|template|create a doc)\b',
    re.IGNORECASE
)

ARTIFACT_HTML_TRIGGERS = re.compile(
    r'\b(html|webpage|landing page|render|visual|dashboard|html artifact)\b',
    re.IGNORECASE
)


def route_intent(user_message: str) -> SkillType:
    """
    Classify user intent to select the appropriate skill.
    Priority: HTML artifact > MD artifact > Ship 30 > default RAG Q&A.
    """
    if ARTIFACT_HTML_TRIGGERS.search(user_message):
        return SkillType.ARTIFACT_HTML
    if ARTIFACT_MD_TRIGGERS.search(user_message):
        return SkillType.ARTIFACT_MARKDOWN
    if SHIP_30_TRIGGERS.search(user_message):
        return SkillType.SHIP_30_ESSAY
    return SkillType.RAG_QA


# ── System Prompts ─────────────────────────────────────────────────────────────

RAG_QA_SYSTEM = """You are the Lenny Growth Assistant — an expert product and growth advisor \
trained exclusively on Lenny's Podcast transcripts.

RULES:
1. ONLY answer from the provided transcript context. Do not use outside knowledge.
2. Always cite your sources using the format: [Source: {episode_title}]
3. If the context doesn't cover the question, say: "Based on the available transcripts, I don't \
have enough information to answer this confidently. The most relevant episode I found is {episode}."
4. Maintain conversation context from prior messages.
5. Be direct, specific, and practical — like a senior growth advisor.
6. Use markdown formatting: headers, bullets, **bold** for key insights."""

NO_CONTEXT_RESPONSE = """I searched through Lenny's Podcast transcripts but couldn't find \
sufficiently relevant content for your question. 

This could mean:
- The topic hasn't been covered in the indexed transcripts yet
- Try rephrasing with different keywords (e.g., "growth loops", "PMF", "pricing", "activation")

I'm currently indexed on episodes covering: product-market fit, growth strategies, PM skills, \
pricing, and North Star metrics."""


def _format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a structured context block."""
    if not chunks:
        return ""
    parts = ["=== TRANSCRIPT CONTEXT ===\n"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}: {chunk.citation}]\n"
            f"{chunk.content}\n"
            f"{'─' * 60}\n"
        )
    return "\n".join(parts)


def _extract_sources(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "episode_title": c.episode_title,
            "episode_number": c.episode_number,
            "guest": c.guest,
            "source_file": c.source_file,
            "citation": c.citation,
            "relevance_score": round(1 - c.distance / 2, 3),
        }
        for c in chunks
    ]


# ── Agent Executor ─────────────────────────────────────────────────────────────

class LennyAgent:
    """
    Core agent executor. Routes to the right skill, retrieves context,
    constructs prompts, and calls the LLM.
    """

    def __init__(self, llm: BaseLLMClient, kb: KnowledgeBaseService):
        self.llm = llm
        self.kb = kb

    async def run(
        self,
        user_message: str,
        history: list[LLMMessage],
        skill_override: Optional[SkillType] = None,
    ) -> AgentResponse:
        """Execute the agent and return a complete response."""
        start = time.time()
        skill = skill_override or route_intent(user_message)
        logger.info("agent_routing", skill=skill, message_preview=user_message[:80])

        # Retrieve context for all skills (grounding is universal)
        chunks = self.kb.retrieve(user_message)
        sources = _extract_sources(chunks)
        avg_score = (
            sum(1 - c.distance / 2 for c in chunks) / len(chunks) if chunks else 0.0
        )

        if skill == SkillType.RAG_QA:
            content = await self._run_rag_qa(user_message, history, chunks)
            artifact_type = None

        elif skill == SkillType.SHIP_30_ESSAY:
            content = await self._run_ship_30(user_message, history, chunks)
            artifact_type = "markdown"

        elif skill == SkillType.ARTIFACT_MARKDOWN:
            content = await self._run_artifact(user_message, history, chunks, "markdown")
            artifact_type = "markdown"

        elif skill == SkillType.ARTIFACT_HTML:
            content = await self._run_artifact(user_message, history, chunks, "html")
            artifact_type = "html"

        else:
            content = await self._run_rag_qa(user_message, history, chunks)
            artifact_type = None

        latency = round((time.time() - start) * 1000)
        logger.info("agent_complete", skill=skill, latency_ms=latency, sources=len(sources))

        return AgentResponse(
            content=content,
            skill_used=skill,
            sources=sources,
            retrieval_score=round(avg_score, 3),
            latency_ms=latency,
            artifact_type=artifact_type,
        )

    async def _run_rag_qa(
        self, query: str, history: list[LLMMessage], chunks: list[RetrievedChunk]
    ) -> str:
        if not chunks:
            return NO_CONTEXT_RESPONSE

        context = _format_context(chunks)
        augmented_query = f"{context}\n\n=== USER QUESTION ===\n{query}"

        messages = history[-8:] + [LLMMessage(role="user", content=augmented_query)]
        return await self.llm.chat(messages, system_prompt=RAG_QA_SYSTEM, temperature=0.4)

    async def _run_ship_30(
        self, query: str, history: list[LLMMessage], chunks: list[RetrievedChunk]
    ) -> str:
        context = _format_context(chunks) if chunks else "No specific context retrieved."
        user_prompt = SHIP_30_USER_TEMPLATE.format(topic=query, context=context)
        messages = [LLMMessage(role="user", content=user_prompt)]
        return await self.llm.chat(messages, system_prompt=SHIP_30_SYSTEM_PROMPT,
                                   temperature=0.7, max_tokens=6000)

    async def _run_artifact(
        self, query: str, history: list[LLMMessage],
        chunks: list[RetrievedChunk], artifact_type: str
    ) -> str:
        context = _format_context(chunks) if chunks else ""
        # Include recent conversation context for artifact generation
        recent_convo = "\n".join(
            f"{m.role.upper()}: {m.content[:500]}"
            for m in history[-4:]
        )
        prompt = build_artifact_prompt(query, context, recent_convo, artifact_type)
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.llm.chat(
            messages, system_prompt=ARTIFACT_SYSTEM_PROMPT,
            temperature=0.6, max_tokens=8000
        )

    async def stream(
        self,
        user_message: str,
        history: list[LLMMessage],
        skill_override: Optional[SkillType] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming version — yields text deltas for SSE."""
        skill = skill_override or route_intent(user_message)
        chunks = self.kb.retrieve(user_message)

        if skill == SkillType.RAG_QA:
            if not chunks:
                yield NO_CONTEXT_RESPONSE
                return
            context = _format_context(chunks)
            augmented = f"{context}\n\n=== USER QUESTION ===\n{user_message}"
            messages = history[-8:] + [LLMMessage(role="user", content=augmented)]
            async for delta in self.llm.stream_chat(messages, system_prompt=RAG_QA_SYSTEM, temperature=0.4):
                yield delta
        else:
            # For structured skills, use non-streaming then yield full response
            response = await self.run(user_message, history, skill)
            yield response.content
