#!/usr/bin/python3.12
"""StockForge - Analyze a single stock with full hypothesis framework."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.recommendation_engine import generate_recommendation, format_stock_report


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_stock.py <SYMBOL>")
        print("Example: python3 analyze_stock.py RELIANCE")
        print()
        print("Popular stocks: RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK,")
        print("                HINDUNILVR, ITC, SBIN, BHARTIARTL, BAJFINANCE")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    print(f"🔍 Analyzing {symbol}...\n")

    rec = generate_recommendation(symbol)
    report = format_stock_report(rec)
    print(report)


if __name__ == "__main__":
    main()
