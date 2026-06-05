#!/bin/bash
# StockForge Setup Script
# Idempotent. Works on any machine with Python 3.10+. Prefers a local .venv
# but falls back to system Python with --break-system-packages if needed.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🏦 StockForge Setup"
echo "===================="
echo "Working directory: $SCRIPT_DIR"

# --- 1. Pick a Python interpreter ---------------------------------------------
PY=""

# Prefer the local venv (created below or pre-existing)
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PY="$SCRIPT_DIR/.venv/bin/python"
    echo "✅ Using existing venv: $PY"
fi

# Then the env override
if [ -z "$PY" ] && [ -n "$STOCKFORGE_PYTHON" ] && [ -x "$STOCKFORGE_PYTHON" ]; then
    PY="$STOCKFORGE_PYTHON"
    echo "✅ Using STOCKFORGE_PYTHON: $PY"
fi

# Then python3 on PATH
if [ -z "$PY" ] && command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
    echo "✅ Using python3 on PATH: $PY"
fi

if [ -z "$PY" ]; then
    echo "❌ No Python 3 interpreter found."
    echo "   Install Python 3.10+ or set STOCKFORGE_PYTHON."
    exit 1
fi

# --- 2. Create venv if it doesn't exist and we have a working python3 -------
if [ "$PY" = "$(command -v python3 2>/dev/null || echo)" ] && [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "📦 Creating local venv at $SCRIPT_DIR/.venv ..."
    if python3 -m venv "$SCRIPT_DIR/.venv" 2>/dev/null; then
        PY="$SCRIPT_DIR/.venv/bin/python"
        echo "✅ Venv created"
    else
        echo "⚠️  venv creation failed; falling back to system Python (will use --break-system-packages)"
    fi
fi

# --- 3. Install dependencies --------------------------------------------------
echo "📦 Installing dependencies..."
if [ -d "$SCRIPT_DIR/.venv" ] && [ "$PY" = "$SCRIPT_DIR/.venv/bin/python" ]; then
    "$PY" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
else
    "$PY" -m pip install --quiet --break-system-packages -r "$SCRIPT_DIR/requirements.txt"
fi

# --- 4. Verify imports --------------------------------------------------------
echo "🔍 Verifying installation..."
"$PY" -c "import yfinance; print('  ✅ yfinance:', yfinance.__version__)"
"$PY" -c "import aynse; print('  ✅ aynse: OK')" 2>/dev/null || echo "  ⚠️  aynse not installed (optional)"
"$PY" -c "import pandas; print('  ✅ pandas:', pandas.__version__)"

# --- 5. Create output dir -----------------------------------------------------
mkdir -p "$SCRIPT_DIR/output"
mkdir -p "$SCRIPT_DIR/output/portfolio"
mkdir -p "$SCRIPT_DIR/output/briefings"
mkdir -p "$SCRIPT_DIR/output/reports"

echo ""
echo "✅ StockForge setup complete!"
echo ""
echo "Python: $PY"
echo ""
echo "Quick start:"
echo "  Daily briefing:   $PY $SCRIPT_DIR/scripts/daily_intelligence.py"
echo "  Top picks:        $PY $SCRIPT_DIR/scripts/daily_top_picks.py"
echo "  Analyze stock:    $PY $SCRIPT_DIR/scripts/analyze_stock.py RELIANCE"
echo "  Screen stocks:    $PY $SCRIPT_DIR/scripts/screen_stocks.py --type fundamental"
echo ""
echo "Optional: copy .env.example to .env and fill in NEWSAPI_KEY for sentiment analysis."
