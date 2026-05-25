#!/bin/bash
# Job Hunt Agent — one-click setup for Mac (M1/M2/M4)
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      Job Hunt Agent — Setup          ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python3 not found. Install from python.org or via: brew install python"
  exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Create venv
cd backend
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Starting Job Hunt Agent server...  ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "👉 Open http://localhost:8000 in your browser"
echo "   Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --port 8000
