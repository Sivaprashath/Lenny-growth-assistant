#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
# Lenny Growth Assistant — One-Step Setup Script
# Configures Python virtual environment, installs dependencies,
# installs frontend npm packages, and verifies environment.
# ══════════════════════════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo "🛠️  Setting up Lenny Growth Assistant..."
echo "============================================================"

# 1. Environment file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "📋 Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi

# 2. Python Virtual Environment
echo "🐍 Setting up Python environment..."
cd "$PROJECT_ROOT/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Created virtualenv at backend/.venv"
fi

source .venv/bin/activate
pip install --upgrade pip -q
echo "📦 Installing backend dependencies from requirements.txt..."
pip install -r requirements.txt -q
echo "✅ Backend dependencies installed."

# 3. Frontend Dependencies
echo "⚛️ Setting up Frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
npm install --silent
echo "✅ Frontend dependencies installed."

echo ""
echo "============================================================"
echo "🎉 Setup complete! You can now run:"
echo "   docker compose up --build      # (Recommended Docker setup)"
echo "   or"
echo "   ./scripts/run_local.sh         # (Native local development)"
echo "============================================================"
