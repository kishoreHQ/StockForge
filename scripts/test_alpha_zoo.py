"""Test alpha zoo and confidence scorer on NSE stocks."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.alpha_zoo import score_all_alphas
from data.market_data import get_history
import pandas as pd

stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BAJFINANCE", "WIPRO", "SBIN", "MARUTI"]

print(f"{'Symbol':15s} {'Alpha':>6s} {'Signal':>12s} {'Themes'}")
print("-" * 70)

for sym in stocks:
    try:
        hist = get_history(sym, period="6mo")
        if hist is None or hist.empty:
            print(f"{sym:15s}  No data")
            continue

        # Convert DataFrame to lists
        price_data = {
            "close": hist["Close"].dropna().tolist() if "Close" in hist.columns else [],
            "high": hist["High"].dropna().tolist() if "High" in hist.columns else [],
            "low": hist["Low"].dropna().tolist() if "Low" in hist.columns else [],
            "volume": hist["Volume"].dropna().tolist() if "Volume" in hist.columns else [],
        }

        if len(price_data["close"]) < 20:
            print(f"{sym:15s}  Insufficient data ({len(price_data['close'])} bars)")
            continue

        result = score_all_alphas(price_data)
        themes_str = " | ".join(f"{k}:{v:.0f}" for k, v in result["themes"].items())
        print(f"{sym:15s} {result['aggregate']:6.1f} {result['signal']:>12s}  {themes_str}")

    except Exception as e:
        print(f"{sym:15s}  ERROR: {e}")
