# Agent Transcripts & Coding Log

This folder contains the record of AI-assisted development decisions, including
failed attempts and corrections. Secrets have been removed.

---

## Session 1 — Initial Architecture Planning

**Tool**: Antigravity (Google DeepMind)  
**Date**: October 10, 2026

**Prompt**: Design the architecture for a RAG-powered assistant with multi-provider LLM support.

**Key decisions reached**:
1. Chose ChromaDB over Pinecone because it runs fully locally — no API key needed for vector store, which aligns with the "local demo" requirement.
2. Chose `sentence-transformers/all-MiniLM-L6-v2` over OpenAI embeddings because it works offline and is free.
3. Decided to implement a factory pattern for LLM clients rather than a plugin/registry pattern — simpler for an evaluator to understand.

**Failed attempt**: Initially considered using LangChain as the RAG framework.
**Correction**: Dropped LangChain in favor of direct ChromaDB + httpx calls. Rationale: LangChain adds abstraction layers that obscure what's happening from an evaluator's perspective. Direct calls are more transparent, more controllable, and faster to debug.

---

## Session 2 — Agent Skill Routing Design

**Prompt**: How should I route between RAG Q&A, Ship 30 essays, and artifact generation?

**Approach tried first**: LLM-based intent classification (ask the model what skill to use).
**Problem**: Adds latency (extra LLM call before the main call), unpredictable, and harder to test.

**Correction**: Switched to regex-based pattern matching (`route_intent()` function).
**Rationale**: Fast, deterministic, testable, and evaluatable without running an LLM. Regex patterns cover the common vocabulary reliably. `skill_override` parameter lets users bypass routing entirely when needed.

---

## Session 3 — Artifact Security Design

**Prompt**: How should HTML artifacts be rendered safely?

**Approaches considered**:
1. Render HTML in a `div` with DOMPurify sanitization
2. Use `<iframe>` with `srcdoc` and `sandbox`
3. Use a CSP header to block script execution

**Selected**: Option 2 — sandboxed iframe with `sandbox="allow-same-origin"` only.

**Rationale**:
- DOMPurify sanitization (Option 1) still allows CSS-based attacks and `<style>` exfiltration via `@import`.
- CSP headers (Option 3) require server configuration and are not portable to the demo context.
- The iframe sandbox is the strongest isolation boundary available in the browser — it creates a separate origin context even for `allow-same-origin`. Crucially, NOT including `allow-scripts` means no JavaScript runs, period.

**What the sandbox blocks**:
- `<script>` tag execution
- Event handlers (`onclick`, `onload`, etc.)
- `fetch`/`XMLHttpRequest` calls
- Form submissions to external URLs
- Navigation away from the page
- Popup windows

---

## Session 4 — Database Schema Decisions

**Prompt**: What should the persistence schema look like?

**Key design decisions**:
1. `sources` stored as JSONB in `messages` table rather than a separate `sources` table.
   - **Rationale**: Sources are always accessed with their message; a JOIN would add complexity with no query flexibility benefit.
2. Soft delete (`is_active` flag) on sessions rather than hard delete.
   - **Rationale**: Safer for demos — accidental deletions are recoverable. Hard delete is a one-line change if needed.
3. `artifact_id` foreign key on messages is nullable and stored at application level.
   - **Rationale**: Not all messages have artifacts; the relationship is 1-to-1 from message → artifact, so a column is simpler than a junction table.

---

## Session 5 — Frontend State Management

**Prompt**: What state manager for the React frontend?

**Zustand chosen over Redux / Context API**.
**Rationale**:
- Redux is overkill for this scale; boilerplate would obscure the logic.
- Context API with `useReducer` is fine but doesn't support async well without extra patterns.
- Zustand is 1KB, has built-in async support, and the store is readable as a single file — evaluators can understand the state shape in 2 minutes.

**SSE streaming state**:
Streaming uses a separate `streamingContent` string that gets cleared after the stream finishes. This avoids mutating the `messages` array mid-stream, which would cause unnecessary re-renders.

---

## Session 6 — Ship 30 Prompt Engineering

**Prompt**: How do you encode Ship 30 for 30 principles in a prompt?

**Failed approach**: "Write a Ship 30 for 30 essay. Follow the Ship 30 guide."
**Problem**: Model doesn't know what Ship 30 principles are without context.

**Correction**: Read the [Ship 30 for 30 guide](https://www.ship30for30.com/post/how-to-start-writing-online-the-ship-30-for-30-ultimate-guide) and encoded the specific principles into the system prompt:
- The 1-1-1 rule (1 idea, 1 reader, 1 emotion)
- Four hook formats with names (Question, Statistic, Contrarian, Story)
- Paragraph length constraints (1-3 sentences max)
- Specific structural arc: Hook → Problem → Insight → Evidence → Takeaway
- The "So What?" test for cutting content

This is the difference between a skill and a prompt — the principles are baked in, not described abstractly.
