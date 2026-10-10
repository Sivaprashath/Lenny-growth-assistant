# Product Requirements Document (PRD)
## The Lenny Growth Assistant

**Version**: 1.0  
**Author**: [Your Name]  
**Status**: Implementation Complete  
**Date**: October 2026

---

## 1. Forward Deployment Brief

### 1.1 User and Problem

**Primary User**: Product managers, growth leads, and startup founders at early-to-mid-stage companies who regularly consume content from Lenny's Podcast and Newsletter.

**Job to be Done**: Access specific, actionable product and growth advice from Lenny's accumulated interview knowledge — without manually searching through 400+ episode transcripts or re-listening to hours of audio.

**Pain Removed**:
- Finding relevant advice currently requires remembering which episode covered a topic, then scrubbing through long transcripts.
- Synthesizing advice across multiple episodes (e.g., "what do 5 different guests say about pricing?") is manually impossible.
- Writing structured content (essays, documents) from transcript insights requires manual summarization and reformatting.

**Secondary User**: Growth writers using the Ship 30 for 30 skill to turn transcript insights into ready-to-publish atomic essays.

---

### 1.2 Success Metrics

**Primary (Operational)**:
> **Grounding rate**: ≥ 80% of assistant responses include at least one cited transcript source with relevance score ≥ 0.5.

**Secondary**:
- Average response latency < 30 seconds on local Ollama (3B model)
- Session creation → first response < 5 seconds (excluding LLM generation time)
- Evaluator can clone + run the system in < 15 minutes following the README

---

### 1.3 Assumptions

| Assumption | Rationale |
|---|---|
| Users are English speakers | All Lenny content is English; multilingual support would require translation pipeline |
| Demo runs on a machine with ≥8GB RAM | Required for local Ollama models (3B model uses ~2.5GB VRAM/RAM) |
| Transcript quality is adequate for chunking | The GitHub repo contains raw text; preprocessing handles noise |
| Users accept ~10–30s latency for local models | This is the inherent trade-off of running local LLMs on consumer hardware |
| Built-in sample transcripts are sufficient for demo | If real transcripts aren't cloned, paraphrased public summaries demonstrate full functionality |
| No real user auth is needed | This is an internal tool / demo — single-tenant, no multi-user auth |
| Artifact security via sandboxing is acceptable | Full CSP headers would require infrastructure changes; iframe sandbox covers the core threat |

---

### 1.4 Scope

#### In Scope (v1)
- ✅ Grounded RAG Q&A from podcast transcripts
- ✅ Ship 30 for 30 essay generation skill
- ✅ Markdown and HTML artifact generation + in-app viewer
- ✅ Session management with persistent history
- ✅ Anthropic Claude, OpenAI, and Ollama (local) LLM support
- ✅ PostgreSQL persistence (Supabase-compatible)
- ✅ Docker Compose one-command startup
- ✅ Structured observability logging
- ✅ Sandboxed HTML artifact rendering

#### Intentionally Excluded (v1)
- ❌ **User authentication** — out of scope for a single-team internal tool demo
- ❌ **Real-time transcript ingestion** — transcripts are a static dataset; webhook refresh is v2
- ❌ **Voice input** — significant complexity for marginal demo value
- ❌ **Multi-model comparison** — showing side-by-side outputs from different providers
- ❌ **Full-text search** — vector semantic search covers the use case adequately
- ❌ **Mobile-native app** — responsive web is sufficient

---

### 1.5 Risks and Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| **Hallucination** | High — users trust AI answers | Strict RAG-only grounding; `NO_CONTEXT_RESPONSE` for low-relevance queries; mandatory source citations |
| **Latency** | Medium — local Ollama can be 20–60s on slower machines | Streaming SSE shows progress in real-time; fallback to cloud is one env var change |
| **Cost** | Medium — cloud LLMs cost money per token | Ollama is free; cloud providers used only if explicitly configured |
| **Data leakage** | Low — transcripts are public; no user PII stored | No auth means no PII; session metadata is user-agent/IP only |
| **Unsafe artifact rendering** | High — HTML injection attack vector | iframe sandbox blocks scripts + external network; CSP headers documented for production |
| **Model quality** | Medium — 3B model may produce weaker essays | Ship 30 prompt is highly structured; 7B model recommended for production |
| **ChromaDB persistence** | Low — local vector store reset on full reindex | Docker volume persists Chroma data; reindex is idempotent |

---

## 2. User Flows

### Flow 1: Grounded Q&A

```
User opens app
  → Clicks "New Chat" OR uses suggestion card
  → Types question (e.g., "How did Airbnb find PMF?")
  → System retrieves top-5 transcript chunks (semantic similarity)
  → LLM generates answer with [Source: Episode X] citations
  → Sources panel shows episode titles + relevance scores
  → User asks follow-up → session history preserved in context
```

### Flow 2: Ship 30 Essay

```
User clicks "✍️ Essay" skill button (or types "write an essay...")
  → Types topic (e.g., "Why retention beats acquisition for growth")
  → System retrieves relevant transcript chunks for grounding
  → LLM generates ~1,250 word essay with Ship 30 structure
  → Essay appears in chat bubble (markdown rendered)
  → Artifact panel auto-opens with markdown document
  → User copies or downloads the .md file
```

### Flow 3: HTML Artifact

```
User clicks "🌐 HTML" skill button
  → "Generate an HTML dashboard about pricing strategies"
  → System generates complete HTML/CSS (no JS, no external URLs)
  → Chat message links to artifact panel
  → Artifact panel shows Preview tab (sandboxed iframe) and Source tab
  → Security notice: "Sandboxed — scripts disabled"
  → User downloads HTML file
```

---

## 3. Acceptance Criteria

| # | Criterion | How to Verify |
|---|---|---|
| AC-1 | Backend returns 200 on `GET /api/health` | `curl http://localhost:8000/api/health` |
| AC-2 | Creating a session returns valid UUID and persists in DB | `POST /api/sessions`, then `GET /api/sessions` |
| AC-3 | Chat response includes sources with episode title | `POST /api/sessions/{id}/chat`, check `sources` array |
| AC-4 | Low-relevance query returns graceful no-context response | Ask "What is the capital of France?" |
| AC-5 | Ship 30 skill produces ~1,250 word essay with hook | Click Essay skill, send topic |
| AC-6 | HTML artifact renders in sandboxed iframe without errors | Ask for HTML page, check Preview tab |
| AC-7 | Switching `LLM_PROVIDER` env var changes provider without code change | Change `.env`, restart backend, check `/api/model` |
| AC-8 | Sessions persist after backend restart | Restart backend, verify sessions still visible |
| AC-9 | Missing Anthropic key falls back to Ollama gracefully | Set `LLM_PROVIDER=anthropic` with no key |
| AC-10 | Evaluator can run system in < 15 minutes | Follow README from scratch |

---

## 4. Implementation Plan

| Phase | Work | Status |
|---|---|---|
| 1 | Config, logging, DB models | ✅ |
| 2 | LLM client factory (Anthropic, OpenAI, Ollama) | ✅ |
| 3 | RAG knowledge base service | ✅ |
| 4 | Agent + skill routing | ✅ |
| 5 | FastAPI routers (sessions, chat, system) | ✅ |
| 6 | React frontend (sidebar, chat, artifact panel) | ✅ |
| 7 | Docker Compose + Dockerfiles | ✅ |
| 8 | Tests + documentation | ✅ |
