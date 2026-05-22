"""StockForge Daily Top Picks — Top 10 growth stocks for next 3 months.

Screens Nifty 200 stocks daily using:
- Alpha Zoo quant factors (10 signals aggregated)
- Fundamental score (ROCE, ROE, debt, growth)
- Technical setup (trend alignment, momentum)
- Valuation (DCF upside)
- Recommendation engine verdict
Returns top 10 ranked by composite growth potential.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_index_constituents, get_quote, get_history
from analysis.alpha_zoo import score_all_alphas
from analysis.technical import full_technical_analysis
from analysis.fundamental import score_fundamentals
from analysis.valuation import dcf_estimate
from intelligence.recommendation_engine import generate_recommendation, _safe_get
from datetime import datetime
import json
import time


def score_growth_potential(symbol: str) -> dict:
    """Score a stock's growth potential for the next 3 months."""
    start = time.time()
    try:
        rec = generate_recommendation(symbol, account_size=500000, risk_pct=2.0)
        alpha = rec.get("alpha_zoo", {})
        tech = rec.get("technical", {})
        fund = rec.get("fundamental", {})
        quote = rec.get("quote", {})
        price = _safe_get(quote, "price", default=0)
        change_pct = _safe_get(quote, "change_pct", default=0)
        volume = _safe_get(quote, "volume", default=0)
        previous_close = _safe_get(quote, "previous_close", default=price)

        # --- Composite growth score (0-100) ---
        score = 50  # baseline

        # Alpha Zoo contribution (0-30 points)
        alpha_agg = alpha.get("aggregate", 50)
        score += (alpha_agg - 50) * 0.6  # -30 to +30

        # Theme bonuses
        themes = alpha.get("themes", {})
        if themes.get("trend", 50) > 60:
            score += 8  # Strong uptrend
        if themes.get("reversal", 50) > 65:
            score += 5  # Oversold bounce potential
        if themes.get("momentum", 50) > 60:
            score += 5
        if themes.get("volume", 50) > 60:
            score += 4  # Volume confirmation

        # Fundamental score (0-20 points)
        fund_score = _safe_get(fund, "score", default=50)
        score += (fund_score - 50) * 0.4  # -20 to +20

        # Valuation bonus
        val = rec.get("valuation", {})
        upside = _safe_get(val, "upside_pct", default=0)
        if isinstance(upside, (int, float)):
            score += min(max(upside, -15), 15) * 0.5  # -7.5 to +7.5

        # Technical trend alignment
        if "signals" in tech:
            bullish = sum(1 for s in tech["signals"] if "✅" in s or "📈" in s)
            bearish = sum(1 for s in tech["signals"] if "⚠️" in s or "📉" in s)
            score += (bullish - bearish) * 3

        # Volume surge (liquidity)
        avg_vol = _safe_get(quote, "avg_volume", default=0)
        if avg_vol and volume:
            vol_ratio = volume / avg_vol if avg_vol > 0 else 1
            if vol_ratio > 1.5:
                score += 3

        # Day performance momentum
        if isinstance(change_pct, (int, float)):
            if change_pct > 1.0:
                score += 2
            elif change_pct < -2.0:
                score -= 3  # Heavy selling pressure

        elapsed = time.time() - start
        return {
            "symbol": symbol.upper(),
            "score": round(max(0, min(100, score)), 1),
            "price": round(price, 2) if price else 0,
            "change_pct": round(change_pct, 2) if isinstance(change_pct, (int, float)) else 0,
            "verdict": rec.get("verdict", "N/A"),
            "confidence": rec.get("confidence", 0),
            "alpha_zoo": alpha_agg,
            "fundamental_score": fund_score,
            "upside": round(upside, 1) if isinstance(upside, (int, float)) else 0,
            "trend_bullish": bullish - bearish if "signals" in tech else 0,
            "sector": _safe_get(fund, "sector", default="N/A"),
            "market_cap": _safe_get(quote, "market_cap", default=0),
            "time_ms": round(elapsed * 1000),
        }
    except Exception as e:
        return {"symbol": symbol.upper(), "score": 0, "error": str(e)}


def get_top_10(universe_size: int = 100, cache_bust: bool = True) -> list:
    """Screen universe and return top 10 growth stocks."""
    universe = get_index_constituents("nifty200")[:universe_size]
    if not universe:
        # Fallback to well-known Nifty stocks
        universe = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
            "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "WIPRO", "AXISBANK", "BAJFINANCE",
            "MARUTI", "SUNPHARMA", "TITAN", "ASIANPAINT", "NTPC", "POWERGRID",
            "M&M", "TATAMOTORS", "ULTRACEMCO", "HCLTECH", "TECHM", "INDUSINDBK",
            "BAJAJFINSV", "NESTLEIND", "HDFCLIFE", "DIVISLAB", "DRREDDY", "CIPLA",
            "SBILIFE", "EICHERMOT", "COALINDIA", "BRITANNIA", "ONGC", "TATASTEEL",
            "JSWSTEEL", "GRASIM", "ADANIPORTS", "HEROMOTOCO", "BPCL", "HINDALCO",
            "BAJAJHLDNG", "APOLLOHOSP", "GODREJCP", "SHREECEM", "HINDZINC", "PIDILITIND",
        ]

    results = []
    total = len(universe)
    for i, sym in enumerate(universe):
        print(f"  [{i+1}/{total}] {sym}...", end=" ", flush=True)
        result = score_growth_potential(sym)
        if result.get("score", 0) > 40:  # Only keep decently-scored
            results.append(result)
        status = "✅" if result.get("score", 0) > 50 else "⏭️"
        print(f"{status} ({result.get('score', 0)})")

    # Sort by score descending
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:15]  # Return 15, we'll display top 10


def format_top_picks(picks: list) -> str:
    """Format top 10 results for display."""
    date = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    lines = []
    lines.append("=" * 70)
    lines.append("📈 STOCKFORGE TOP 10 GROWTH PICKS — 3 Month Outlook")
    lines.append(f"   {date}")
    lines.append("=" * 70)

    if not picks:
        lines.append("\n  No stocks scored above threshold.")
        return "\n".join(lines)

    # Table header
    lines.append("\n  # │ Symbol          │ Score │ Price    │ Chg%  │ Verdict        │ α-Zoo │ Fund  │ Upside │ Trend")
    lines.append("  ──┼─────────────────┼───────┼──────────┼───────┼────────────────┼───────┼───────┼────────┼──────")

    for i, p in enumerate(picks[:10], 1):
        sym = f"{p['symbol']:<15s}"
        score_icon = "🔥" if p['score'] >= 75 else "✅" if p['score'] >= 65 else "📈" if p['score'] >= 55 else "➡️"
        price_str = f"₹{p['price']:<8.2f}" if p['price'] else f"{'N/A':<10s}"
        chg = p.get('change_pct', 0)
        chg_str = f"{chg:+.1f}%" if isinstance(chg, (int, float)) else "N/A"
        verdict = f"{p['verdict']:<14s}"[:14]
        alpha = p.get('alpha_zoo', 50)
        fund = p.get('fundamental_score', 50)
        upside = p.get('upside', 0)
        up_str = f"{upside:+.1f}%" if isinstance(upside, (int, float)) else "N/A"
        trend = f"{p.get('trend_bullish', 0):+d}" if p.get('trend_bullish', 0) else "0"

        lines.append(f"  {i:2d}│ {sym}│ {score_icon}{p['score']:<4.1f} │ {price_str}│ {chg_str:<5s} │ {verdict}│ {alpha:<5.1f}│ {fund:<5.1f}│ {up_str:<6s}│ {trend}")

    # Summary
    lines.append(f"\n{'─' * 70}")
    lines.append(f"  Screened: {len(picks)} stocks | Top 10 shown | Updated: {date}")
    lines.append(f"  Methodology: Alpha Zoo(10 factors) + Technical + Fundamental + Valuation")
    lines.append(f"{'=' * 70}")

    # Key insights
    top = picks[:3]
    lines.append(f"\n🔑 Top 3 Picks:")
    for i, p in enumerate(top, 1):
        lines.append(f"  {i}. {p['symbol']} — Score: {p['score']}/100 | ₹{p['price']} | {p['verdict']}")
        lines.append(f"     Alpha Zoo: {p.get('alpha_zoo', 'N/A')}/100 | RSI/MACD trend: {p.get('trend_bullish', 0)}")

    lines.append(f"\n⚠️  Not investment advice. Do your own research before investing.")
    return "\n".join(lines)


if __name__ == "__main__":
    print("🔍 StockForge Daily Top 10 Growth Picks\n")
    print(f"  Screening Nifty 200 at {datetime.now().strftime('%H:%M IST')}")
    print(f"  This will take 2-4 minutes for 100 stocks...\n")
    picks = get_top_10(universe_size=100)
    print(f"\n{'=' * 70}\n")
    print(format_top_picks(picks))
