# Architecture Document
## The Lenny Growth Assistant

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser Client                          │
│  React + Vite + Zustand  ·  SSE Streaming  ·  Artifact Viewer  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP / SSE
┌───────────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│                                                                 │
│  ┌─────────────┐  ┌────────────────────┐  ┌─────────────────┐  │
│  │  Session    │  │   Chat / Stream    │  │  System/Health  │  │
│  │  Router     │  │   Router           │  │  Router         │  │
│  └──────┬──────┘  └─────────┬──────────┘  └────────┬────────┘  │
│         │                   │                       │           │
│  ┌──────▼───────────────────▼──────────────────────▼────────┐  │
│  │              LennyAgent (Intent Router + Executor)        │  │
│  │   route_intent() → RAG QA | Ship30 | MD Artifact | HTML  │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│          ┌──────────────────┼──────────────────────┐            │
│  ┌───────▼──────┐   ┌───────▼──────┐   ┌───────────▼──────┐   │
│  │   LLM Client │   │  Knowledge   │   │   Skill Library  │   │
│  │   Factory    │   │   Base (RAG) │   │  ship_30.py      │   │
│  │  Anthropic / │   │  ChromaDB    │   │  artifact_gen.py │   │
│  │  OpenAI /    │   │  + SentTrans │   │                  │   │
│  │  Ollama      │   │              │   │                  │   │
│  └───────┬──────┘   └───────┬──────┘   └──────────────────┘   │
│          │                  │                                   │
└──────────┼──────────────────┼───────────────────────────────────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────────────────────────────┐
    │  Ollama     │    │  PostgreSQL (via asyncpg)            │
    │  (local)    │    │  Sessions · Messages · Artifacts     │
    │  or Cloud   │    │  (Supabase-compatible)               │
    └─────────────┘    └──────────────────────────────────────┘
```

---

## 2. Database Schema

### Sessions Table
```sql
CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(255),
    user_metadata JSONB,
    model_provider VARCHAR(50) NOT NULL DEFAULT 'ollama',
    model_name  VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    is_active   BOOLEAN DEFAULT TRUE
);
```

### Messages Table
```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- user | assistant
    content         TEXT NOT NULL,
    token_count     INTEGER,
    latency_ms      FLOAT,
    sources         JSONB,     -- [{episode_title, episode_number, guest, citation, relevance_score}]
    retrieval_score FLOAT,
    skill_used      VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Artifacts Table
```sql
CREATE TABLE artifacts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_id    UUID REFERENCES messages(id) ON DELETE CASCADE,
    artifact_type VARCHAR(20) NOT NULL,  -- markdown | html
    title         VARCHAR(255),
    content       TEXT NOT NULL,
    size_bytes    INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 3. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | System health (DB, LLM, KB status) |
| `GET` | `/api/model` | Current LLM provider + available options |
| `POST` | `/api/sessions` | Create a new chat session |
| `GET` | `/api/sessions` | List sessions (paginated) |
| `GET` | `/api/sessions/{id}` | Get session detail |
| `DELETE` | `/api/sessions/{id}` | Soft-delete session |
| `POST` | `/api/sessions/{id}/chat` | Send message, get full response |
| `POST` | `/api/sessions/{id}/stream` | Send message, get SSE stream |
| `GET` | `/api/sessions/{id}/messages` | Get conversation history |
| `GET` | `/api/artifacts/{id}` | Fetch artifact by ID |
| `POST` | `/api/kb/reindex` | Trigger knowledge base reindex |

### Request / Response Contract: `POST /api/sessions/{id}/chat`

**Request:**
```json
{
  "message": "How did Airbnb find product-market fit?",
  "skill_override": null,  // null | "rag_qa" | "ship_30_essay" | "artifact_markdown" | "artifact_html"
  "stream": false
}
```

**Response:**
```json
{
  "message": {
    "id": "uuid",
    "session_id": "uuid",
    "role": "assistant",
    "content": "...",
    "skill_used": "rag_qa",
    "sources": [
      {
        "episode_title": "How Airbnb Found Product-Market Fit",
        "episode_number": "1",
        "guest": "Brian Chesky",
        "citation": "Episode 1 – \"How Airbnb Found Product-Market Fit\" – with Brian Chesky",
        "relevance_score": 0.87
      }
    ],
    "retrieval_score": 0.82,
    "latency_ms": 4300,
    "artifact_id": null,
    "created_at": "2026-10-10T..."
  },
  "artifact": null  // or ArtifactResponse if generated
}
```

---

## 4. Ingestion & Retrieval Flow

```
Transcript files (.txt, .md)
        │
        ▼
TranscriptIngester.ingest()
  ├── Parse metadata from filename (episode number, title)
  ├── Clean and normalize text
  └── Sliding window chunking (1000 chars, 200 overlap)
        │
        ▼
ChromaDB.upsert()
  ├── SentenceTransformer embeddings ("all-MiniLM-L6-v2")
  └── Metadata stored: episode_title, episode_number, guest, chunk_index
        │
        ▼  [at query time]
ChromaDB.query(query_texts=[user_question], n_results=5)
  ├── Returns top-5 chunks by cosine similarity
  └── Filtered by similarity_threshold = 0.3
        │
        ▼
Context injection into LLM prompt
  ├── [Source 1: Episode X "Title" – with Guest]
  ├── chunk content
  └── USER QUESTION: ...
```

---

## 5. Agent Routing

```python
def route_intent(message: str) -> SkillType:
    if HTML_PATTERN.search(message)       → ARTIFACT_HTML
    if MARKDOWN_PATTERN.search(message)   → ARTIFACT_MARKDOWN
    if SHIP_30_PATTERN.search(message)    → SHIP_30_ESSAY
    else                                  → RAG_QA  (default)
```

The router uses regex pattern matching on trigger keywords. The evaluator can override routing via `skill_override` in the API or the skill selector buttons in the UI.

---

## 6. Model Toggle Architecture

```
.env: LLM_PROVIDER=ollama

get_cached_llm_client()
  └── get_llm_client(settings)
        ├── LLM_PROVIDER=anthropic → AnthropicClient (if key set)
        │                         → OllamaClient (fallback if no key)
        ├── LLM_PROVIDER=openai   → OpenAIClient (if key set)
        │                         → OllamaClient (fallback if no key)
        └── LLM_PROVIDER=ollama   → OllamaClient
```

The client is a singleton, cached after first initialization. Provider info is visible in:
- UI sidebar (model badge)
- `GET /api/model` endpoint
- Startup logs

---

## 7. Security Architecture

### Artifact Rendering

**Threat model**: The LLM may generate malicious HTML (prompt injection → XSS → data exfiltration).

**Mitigations**:
1. **iframe sandbox**: `sandbox="allow-same-origin"` — blocks:
   - Script execution (`allow-scripts` NOT included)
   - Form submissions (`allow-forms` NOT included)
   - Popups (`allow-popups` NOT included)
   - External navigation
2. **Artifact size limit**: 512KB max prevents memory exhaustion
3. **No `allow-scripts`**: Even embedded `<script>` tags are inert
4. **Source view** shows raw content for manual inspection

**What is permitted in the sandbox**:
- CSS rendering (styling, animations) ✓
- HTML structure ✓
- Static images (base64 only — external URLs blocked by browser's origin policy) ✓
- Google Fonts via `@import` (CSS read-only, no script execution) ✓

---

## 8. Deployment Topology

### Development
```
localhost:3000 (Vite) → proxy → localhost:8000 (FastAPI) → localhost:5432 (PostgreSQL)
                                                         → localhost:11434 (Ollama)
```

### Docker Compose
```
container: lenny_frontend (nginx:80) → proxy → container: lenny_backend (:8000)
                                                   → container: lenny_db (postgres:5432)
                                                   → host.docker.internal:11434 (Ollama)
```

### Production (Supabase + Cloud LLM)
```
Vercel/Netlify (frontend) → backend service (Railway/Fly.io)
                               → Supabase (PostgreSQL)
                               → Anthropic/OpenAI API
```
