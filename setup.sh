#!/bin/bash
# StockForge Setup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYS_PYTHON="/usr/bin/python3.12"

echo "🏦 StockForge Setup"
echo "===================="

# Check Python
if [ ! -f "$SYS_PYTHON" ]; then
    echo "❌ Python 3.12 not found"
    exit 1
fi

echo "✅ Python: $($SYS_PYTHON --version)"

# Install dependencies
echo "📦 Installing dependencies..."
$SYS_PYTHON -m pip install --break-system-packages -r "$SCRIPT_DIR/requirements.txt" --quiet

# Verify installation
echo "🔍 Verifying installation..."
$SYS_PYTHON -c "import yfinance; print('✅ yfinance:', yfinance.__version__)"
$SYS_PYTHON -c "import aynse; print('✅ aynse OK')"
$SYS_PYTHON -c "import pandas; print('✅ pandas:', pandas.__version__)"

# Create output dir
mkdir -p "$SCRIPT_DIR/output"

echo ""
echo "✅ StockForge setup complete!"
echo ""
echo "Quick start:"
echo "  Daily briefing:  python3 $SCRIPT_DIR/scripts/daily_intelligence.py"
echo "  Analyze stock:   python3 $SCRIPT_DIR/scripts/analyze_stock.py RELIANCE"
echo "  Screen stocks:   python3 $SCRIPT_DIR/scripts/screen_stocks.py --type fundamental"
echo ""
