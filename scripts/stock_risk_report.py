"""StockForge Portfolio Risk Report Script

Generates a comprehensive risk report for a specific stock or portfolio,
integrating confidence scoring and dynamic TP/SL levels.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_quote, get_history
from analysis.technical import full_technical_analysis
from risk.confidence_scorer import StockForgeConfidenceScorer
from risk.dynamic_tp_sl import DynamicTPSL
from risk import generate_risk_report


def analyze_stock_risk(symbol: str, account_size: float = 500000, risk_pct: float = 2.0):
    """Generate full risk analysis for a stock."""
    print(f"\n{'='*65}")
    print(f"📊 STOCKFORGE RISK ANALYSIS — {symbol.upper()}")
    print(f"{'='*65}")

    quote = get_quote(symbol)
    price = quote.get("price", 0)
    if not price:
        print("❌ No price data available")
        return

    print(f"\n💰 Price: ₹{price:.2f}")
    print(f"{'─'*50}")

    # 1. Technical analysis (for indicators + ATR)
    tech = full_technical_analysis(symbol)
    atr = tech.get("atr", price * 0.02) if isinstance(tech.get("atr"), (int, float)) else price * 0.02

    # 2. Confidence scoring
    print("\n🎯 CONFIDENCE SCORE")
    print("-" * 40)

    confidence = StockForgeConfidenceScorer.score_from_stockforge_rec({
        "technical": tech,
        "quote": quote,
        "fundamental": {"score": 50},
    })

    print(f"  Score: {confidence['confidence']:.3f} / 1.0")
    print(f"  Rating: {confidence['rating']}")
    print(f"  Action: {confidence['action']}")
    print(f"  Breakdown:")
    for factor, score in confidence["breakdown"].items():
        if score is not None:
            print(f"    {factor}: {score}")

    # 3. Dynamic TP/SL levels
    print(f"\n📐 DYNAMIC TP/SL LEVELS")
    print("-" * 40)

    # Get price history for volatility estimation
    hist = get_history(symbol, period="1mo")
    prices = hist.get("Close", []) if isinstance(hist, dict) else []

    tpsl_report = DynamicTPSL.generate_report(
        entry=price,
        direction="long",
        atr=atr if isinstance(atr, (int, float)) else None,
        prices=prices,
    )
    print(tpsl_report)

    # 4. Full risk management report (existing)
    print(f"\n{'-'*50}")
    print("Full risk report from existing system:")
    print(f"{'-'*50}")

    sl_2x = price - (atr * 2)
    target = price * 1.2

    risk_report = generate_risk_report(
        account_size=account_size,
        entry_price=price,
        stop_loss_price=max(round(sl_2x, 2), round(price * 0.92, 2)),
        target_price=round(target, 2),
        atr=atr if isinstance(atr, (int, float)) else None,
        risk_pct=risk_pct,
    )
    print(f"\n{risk_report}")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    analyze_stock_risk(symbol)
