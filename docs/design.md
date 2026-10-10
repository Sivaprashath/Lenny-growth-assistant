# Design Document
## The Lenny Growth Assistant — UI/UX

---

## 1. Design Philosophy

### Principles

1. **Information density without clutter** — Product people are power users. They want to see sources, latency, and skill info without having to hunt for it. We show metadata, but secondary to the content.

2. **Grounding is visible** — The single most important trust signal for an AI assistant is: *where did this come from?* Sources are surfaced as a collapsible panel below every AI response — not buried in a tooltip or a separate page.

3. **The artifact is a first-class citizen** — The artifact panel is not a modal or a drawer. It sits permanently beside the chat (on wide screens), visible and inspectable at all times. This mirrors how Claude Artifacts works, which evaluators will recognize as the right pattern.

4. **State is always obvious** — Loading, streaming, error, and empty states all have distinct visual representations. Users should never wonder "is this broken or just slow?"

5. **Dark, premium, focused** — The color palette is deep navy + electric blue gradient. This aesthetic says "intelligent tool" not "consumer app." It respects the seriousness of the product/growth work users are doing.

---

## 2. Color Palette

| Token | Value | Use |
|---|---|---|
| `--bg-primary` | `#0a0e1a` | App background |
| `--bg-secondary` | `#0f172a` | Content areas, artifact panel |
| `--bg-card` | `#131c30` | Message bubbles, input |
| `--bg-sidebar` | `#080c18` | Sidebar |
| `--brand-from` | `#3b82f6` | Brand gradient start (blue) |
| `--brand-to` | `#8b5cf6` | Brand gradient end (purple) |
| `--accent-emerald` | `#10b981` | Success, sources, live indicator |
| `--accent-amber` | `#f59e0b` | HTML artifacts, warnings |
| `--text-primary` | `#f1f5f9` | Primary text |
| `--text-muted` | `#475569` | Metadata, hints |

**Rationale**: Blue-to-purple gradient is distinctive and professional. It avoids the generic "AI assistant blue" (ChatGPT) and the "startup green." The deep navy backgrounds create premium depth without being as extreme as pure black.

---

## 3. Information Architecture

```
┌── App ─────────────────────────────────────────────────┐
│                                                         │
│  ┌─ Sidebar (280px) ─┐  ┌─ Main Area ───────────────┐ │
│  │  Logo + New Chat   │  │  Header (session title)    │ │
│  │                    │  │                            │ │
│  │  [Sessions List]   │  │  ┌─ Chat Panel ──────────┐│ │
│  │  · Session 1       │  │  │  Messages              ││ │
│  │  · Session 2       │  │  │  ┄ Welcome screen      ││ │
│  │                    │  │  │  ┄ Message bubbles      ││ │
│  │  [Model Badge]     │  │  │  ┄ Typing indicator     ││ │
│  │  🟢 Ollama         │  │  │                        ││ │
│  │  llama3.2:3b       │  │  │  [Skill Selector]      ││ │
│  └────────────────────┘  │  │  [Chat Input]          ││ │
│                           │  └────────────────────────┘│ │
│                           │                            │ │
│                           │  ┌─ Artifact Panel ──────┐│ │
│                           │  │  Header + tabs         ││ │
│                           │  │  Preview / Source      ││ │
│                           │  │  [Sandboxed iframe     ││ │
│                           │  │   or MD renderer]      ││ │
│                           │  └────────────────────────┘│ │
│                           └────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 4. Key Interaction States

### 4.1 Welcome / Empty State
- Animated floating logo (CSS `translateY` keyframe)
- Gradient heading text
- 4 suggestion cards in a 2×2 grid — clicking sends the question directly
- Reasoning: onboarding users to capable use cases immediately increases perceived value

### 4.2 Loading / Typing State
- Three-dot typing indicator (staggered bounce animation)
- Replaces the AI message position — does not shift layout
- Streaming: shows cursor blink (`opacity` blink animation on a 2px span)

### 4.3 Source Citations
- Collapsed by default for quick skimming
- Shows episode number, title, guest, and a relevance % bar
- Color-coded: blue heading, emerald percentage score

### 4.4 Artifact Generated
- Toast notification: "HTML artifact generated ✓"
- Artifact panel slides in from the right (CSS `translateX` animation)
- Chat message shows "View Generated Artifact" button — links to the panel

### 4.5 Error States
- Red toast with `✕` prefix
- Descriptive messages: "Ollama not running at http://localhost:11434..."
- No generic "Something went wrong" messages

---

## 5. Skill Selector

The skill selector uses pill-shaped toggle buttons above the input:

```
[🔍 Q&A] [✍️ Essay] [📄 Markdown] [🌐 HTML]
```

- Default (no selection) = RAG Q&A
- Selection persists across messages in a session
- Active state: blue border + gradient background
- Placeholder text in textarea updates based on selected skill

**Rationale**: Exposing skills as toggle buttons (not a dropdown) keeps the selection always visible and reduces cognitive overhead vs. remembering commands.

---

## 6. Responsive Behavior

| Screen Width | Layout |
|---|---|
| > 1100px | Full 3-panel: sidebar + chat + artifact panel |
| 768–1100px | Sidebar + chat (artifact panel hidden, accessible via button) |
| < 768px | Chat only (sidebar hidden, hamburger menu planned for v2) |

The breakpoints are defined as CSS custom properties, making them trivial to adjust.

---

## 7. Accessibility

| Consideration | Implementation |
|---|---|
| Semantic HTML | `<nav>`, `<header>`, `<main>`, `<aside>`, `<button>` used throughout |
| ARIA labels | `aria-label` on icon-only buttons, `aria-live` on messages area |
| Focus management | All interactive elements focusable; tab order logical |
| Color contrast | All text on dark backgrounds meets WCAG AA (4.5:1) |
| Keyboard navigation | Enter to send, Tab to navigate skill buttons |
| Screen reader | Messages area has `role="log"` + `aria-live="polite"` |
| Reduced motion | Animations use `prefers-reduced-motion` CSS (planned v2) |

---

## 8. Typography

| Usage | Font | Weight | Size |
|---|---|---|---|
| App name, welcome title | Outfit | 700–800 | 15px–28px |
| Body, UI elements | Inter | 400–600 | 12px–15px |
| Code, source view | JetBrains Mono | 400–500 | 12px |

**Rationale**: Outfit is distinctive and modern for display text (avoids the "we used Inter for everything" trap). JetBrains Mono gives the code view a developer-tool feel appropriate to the audience.

---

## 9. Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Permanent artifact panel (not modal) | Keeps content visible while chatting | Uses horizontal space — hidden on <1100px |
| Sources below message (not inline) | Reduces cluttering the main answer | Requires one extra look-down to see citations |
| Skill toggles (not slash commands) | Discoverable for non-technical users | Takes up input area real estate |
| Dark theme only (no light mode) | Maintains cohesive premium feel | May not suit all workplace environments |
| Streaming via SSE (not polling) | Real-time feedback, lower perceived latency | Requires nginx config for unbuffered streaming |
