#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
# Lenny Growth Assistant — Local Development Launcher
# Starts backend and frontend concurrently for evaluation
# ══════════════════════════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "============================================================"
echo "🎙️  Starting Lenny Growth Assistant (Local Dev Mode)"
echo "============================================================"

# Ensure .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi

# Ensure data directory exists
mkdir -p "$PROJECT_ROOT/data/transcripts"
mkdir -p "$PROJECT_ROOT/data/chroma"

# Trap SIGINT/SIGTERM to kill child processes
cleanup() {
    echo ""
    echo "🛑 Shutting down Lenny Growth Assistant..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend
echo "🚀 Starting FastAPI backend on http://localhost:8000..."
cd "$BACKEND_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set DATABASE_URL fallback to local sqlite if postgres not running
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///$PROJECT_ROOT/data/lenny.db}"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 2. Start Frontend
echo "✨ Starting Vite React frontend on http://localhost:3000..."
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

npm run dev -- --host 0.0.0.0 --port 3000 &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "🎉 Lenny Growth Assistant is LIVE!"
echo "   - Web App:      http://localhost:3000"
echo "   - API Docs:     http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/api/health"
echo "============================================================"
echo "Press Ctrl+C to stop all servers."

# Wait for processes
wait
