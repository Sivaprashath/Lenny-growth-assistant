# The Lenny Growth Assistant

> An AI-powered product and growth advisor grounded in Lenny's Podcast transcripts.
> Answers complex PM questions, generates Ship 30 for 30 essays, and creates renderable Markdown/HTML artifacts.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-local_LLM-black)](https://ollama.com)

---

## 🗂️ Project Structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── api/                 # Routers: sessions, chat, system
│   │   ├── agents/              # LennyAgent + intent router
│   │   ├── core/                # Config, logging, LLM factory
│   │   ├── db/                  # SQLAlchemy models + engine
│   │   ├── services/            # RAG / knowledge base
│   │   └── skills/              # Ship 30, artifact generation
│   ├── tests/                   # pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root layout
│   │   ├── components/          # Chat, Artifact panels
│   │   ├── lib/api.js           # API client + SSE streaming
│   │   └── store/index.js       # Zustand state
│   └── Dockerfile
├── docs/                        # PRD, architecture, design docs
├── docker-compose.yml
└── .env.example
```

---

## ⚡ Quick Start (Docker — One Command)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) running locally (for demo)

### 1. Clone and configure

```bash
git clone <your-repo-url> lenny-growth-assistant
cd lenny-growth-assistant
cp .env.example .env
```

### 2. Start Ollama and pull the demo model

```bash
# In a separate terminal:
ollama serve

# Pull the model (one-time, ~2GB):
ollama pull llama3.2:3b
```

### 3. Launch everything

```bash
docker compose up --build
```

**That's it.** Open [http://localhost:3000](http://localhost:3000) in your browser.

- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

---

## 🔧 Local Development (Without Docker)

### Backend

```bash
cd backend

# Create virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp ../.env.example .env
# Edit .env — at minimum set DATABASE_URL

# Run (auto-reloads on save)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Opens http://localhost:3000
```

---

## 🤖 LLM Provider Configuration

Switch providers by editing **one line** in `.env` — no code changes required:

| Provider | `.env` setting | Requirement |
|---|---|---|
| **Ollama (demo)** | `LLM_PROVIDER=ollama` | `ollama serve` running locally |
| **Anthropic Claude** | `LLM_PROVIDER=anthropic` | `ANTHROPIC_API_KEY=sk-ant-...` |
| **OpenAI** | `LLM_PROVIDER=openai` | `OPENAI_API_KEY=sk-...` |

### Ollama Model Options

```bash
ollama pull llama3.2:3b     # 2GB  — fast, good quality (recommended)
ollama pull mistral:7b      # 4GB  — better quality
ollama pull phi3:mini       # 2GB  — very fast
ollama pull gemma2:2b       # 1.6GB — lightest
```

**Fallback behavior**: If `ANTHROPIC_API_KEY` is missing when `LLM_PROVIDER=anthropic`, the system automatically falls back to Ollama and logs a warning. No crash, no silent failure.

---

## 📚 Knowledge Base

The assistant uses transcript files from [Lenny's Podcast GitHub](https://github.com/ChatPRD/lennys-podcast-transcripts).

### Add transcripts

```bash
# Clone the transcripts repo into backend/data/transcripts/
git clone https://github.com/ChatPRD/lennys-podcast-transcripts backend/data/transcripts

# Trigger reindex (or it happens on backend startup)
curl -X POST http://localhost:8000/api/kb/reindex
```

**Without real transcripts**: The system automatically uses built-in sample excerpts covering Airbnb/Chesky, North Star metrics, pricing strategy, and PM skills — sufficient for a demo.

---

## 🎯 Skills

| Skill | Trigger keywords | Example prompt |
|---|---|---|
| **RAG Q&A** | (default) | "What is the North Star metric?" |
| **Ship 30 Essay** | "essay", "write", "draft", "ship 30" | "Write a Ship 30 essay on growth loops" |
| **Markdown Artifact** | "markdown", "document", "template" | "Create a markdown playbook on PMF" |
| **HTML Artifact** | "html", "webpage", "landing page" | "Generate an HTML dashboard on pricing" |

You can also force a skill using the skill selector buttons in the UI.

---

## 🧪 Running Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-anyio httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Manual Test Plan (UI)

1. **New session**: Click "New Chat" → verify session appears in sidebar
2. **Q&A**: Ask "How did Airbnb find product-market fit?" → verify grounded answer with sources
3. **Ship 30**: Type "Write a Ship 30 essay on North Star metrics" → verify ~1,250 word essay with hook
4. **Markdown artifact**: "Create a markdown document about pricing strategy" → verify artifact panel opens
5. **HTML artifact**: "Generate an HTML landing page about growth loops" → verify sandboxed preview
6. **Session persistence**: Refresh page → verify session and messages still exist
7. **Model badge**: Check sidebar model badge shows current provider

---

## 🔍 Observability & Troubleshooting

### Structured logs

All backend logs are structured JSON (or colorized in DEBUG mode):

```bash
# Follow backend logs
docker compose logs -f backend

# Check for errors
docker compose logs backend | grep '"level":"error"'

# Check retrieval performance  
docker compose logs backend | grep "retrieval_complete"
```

### Common issues

| Problem | Solution |
|---|---|
| Ollama timeout | Increase `OLLAMA_TIMEOUT` in `.env`, or use a smaller model |
| DB connection refused | Check `DATABASE_URL` and that PostgreSQL is running |
| Empty retrieval results | Check `backend/data/transcripts/` has `.txt` or `.md` files |
| CORS errors | Set `FRONTEND_ORIGIN` to match your frontend URL |
| Artifact panel blank | Check browser console — HTML rendering errors will show |

---

## 🚀 Environment Variables Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `LLM_PROVIDER` | `ollama` | ✓ | `ollama`, `anthropic`, or `openai` |
| `OLLAMA_MODEL` | `llama3.2:3b` | ✓ | Any model available in your Ollama |
| `ANTHROPIC_API_KEY` | — | If using Anthropic | Claude API key |
| `OPENAI_API_KEY` | — | If using OpenAI | OpenAI API key |
| `DATABASE_URL` | `postgresql+asyncpg://...` | ✓ | Async PostgreSQL connection |
| `SECRET_KEY` | dev value | ✓ in prod | Random 32-byte hex string |
| `LOG_LEVEL` | `INFO` | ✗ | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `TOP_K_RETRIEVAL` | `5` | ✗ | Number of transcript chunks to retrieve |
| `TRANSCRIPTS_DIR` | `./data/transcripts` | ✗ | Path to transcript files |

---

## 🔐 Security Notes

- **HTML artifacts** are rendered in `<iframe sandbox="allow-same-origin">` — JavaScript execution and external network calls are blocked.
- **Never commit `.env`** — it's in `.gitignore`.
- **SQL injection** is prevented by SQLAlchemy's parameterized queries.
- **Artifact size** is limited to 512KB by default (`ARTIFACT_MAX_SIZE_KB`).

---

## 📄 Deliverables

| # | File | Location |
|---|---|---|
| 1 | Source code | This repository |
| 2 | README | `README.md` |
| 3 | PRD | `docs/PRD.md` |
| 4 | Design doc | `docs/design.md` |
| 5 | Architecture | `docs/architecture.md` |
| 6 | Agent transcripts | `agent_transcripts/` |
| 7 | Tests | `backend/tests/` |
| 8 | Demo video | [YouTube link] |

---

## 📜 License

MIT — built for the Oogway Labs Forward Deployed Engineer assignment.
