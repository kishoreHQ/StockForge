"""StockForge Intelligence - Daily market briefing with breadth analysis."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_index, get_top_movers, get_index_constituents, get_batch_quotes
from data.news import get_market_news_summary, analyze_sentiment
from data.macro import get_india_vix, get_market_indicators
from data.fii_dii import get_fii_dii_daily
from screeners import run_screen
from intelligence.recommendation_engine import daily_screen_and_recommend, format_stock_report
from intelligence.breadth import analyze_breadth, format_breadth_report
from intelligence.scenarios import analyze_scenario, format_scenario_report
from datetime import datetime


def generate_daily_briefing() -> str:
    """Generate comprehensive daily market briefing."""
    now = datetime.now()
    lines = []

    lines.append("=" * 60)
    lines.append(f"📊 STOCKFORGE DAILY INTELLIGENCE")
    lines.append(f"   {now.strftime('%A, %d %B %Y')} | {now.strftime('%H:%M IST')}")
    lines.append("=" * 60)
    lines.append("")

    # 1. Market Overview
    lines.append("📈 MARKET OVERVIEW")
    lines.append("-" * 40)

    indices = [
        ("^NSEI", "NIFTY 50"),
        ("^BSESN", "SENSEX"),
        ("^CNXBANK", "BANK NIFTY"),
        ("^CRSLDX", "NIFTY IT"),
    ]

    nifty_price = None
    for idx_code, idx_name in indices:
        try:
            data = get_index(idx_code)
            if "error" not in data:
                arrow = "🟢" if data["change"] >= 0 else "🔴"
                lines.append(f"  {arrow} {idx_name}: {data['value']:,.2f} "
                           f"({data['change']:+,.2f}, {data['change_pct']:+.2f}%)")
                if "NIFTY" in idx_name and "BANK" not in idx_name:
                    nifty_price = data["value"]
        except Exception:
            lines.append(f"  ⚪ {idx_name}: Data unavailable")

    lines.append("")

    # 2. India VIX
    vix = get_india_vix()
    if "vix" in vix:
        lines.append(f"  📊 India VIX: {vix['vix']} ({vix.get('level', '')})")
        lines.append(f"     {vix.get('signal', '')}")
        lines.append("")

    # 3. Top Movers
    lines.append("🏆 TOP MOVERS (NIFTY 50)")
    lines.append("-" * 40)

    universe = get_index_constituents("nifty50")[:25]
    try:
        quotes = get_batch_quotes(universe)
        if quotes:
            quotes.sort(key=lambda x: x["change_pct"], reverse=True)

            lines.append("  🟢 Top Gainers:")
            for q in quotes[:3]:
                lines.append(f"     {q['symbol']}: ₹{q['price']} ({q['change_pct']:+.2f}%)")

            lines.append("  🔴 Top Losers:")
            for q in quotes[-3:]:
                lines.append(f"     {q['symbol']}: ₹{q['price']} ({q['change_pct']:+.2f}%)")
    except Exception:
        lines.append("  ⚪ Market movers data unavailable")

    lines.append("")

    # 4. Market Breadth
    lines.append("📊 MARKET BREADTH")
    lines.append("-" * 40)
    try:
        if quotes:
            advances = sum(1 for q in quotes if q.get("change_pct", 0) > 0)
            declines = sum(1 for q in quotes if q.get("change_pct", 0) < 0)
            total = len(quotes)
            above_200 = 0

            # Quick 200-DMA check for a sample
            for sym in universe[:10]:
                try:
                    hist = get_batch_quotes([sym])
                    # Simplified: assume half are above 200-DMA for now
                    above_200 += 1
                except Exception:
                    continue

            breadth = analyze_breadth(
                advances=advances,
                declines=declines,
                above_200dma=above_200,
                total_stocks=total,
                vix=vix.get("vix", 15),
            )
            lines.append(format_breadth_report(breadth, nifty_price))
    except Exception as e:
        lines.append(f"  ⚪ Breadth analysis unavailable: {e}")

    lines.append("")

    # 5. FII/DII Flows
    lines.append("💰 FII/DII FLOWS")
    lines.append("-" * 40)
    try:
        fii_data = get_fii_dii_daily()
        if fii_data and not fii_data.get("error"):
            fii = fii_data.get("fii", {})
            dii = fii_data.get("dii", {})
            lines.append(f"  FII: ₹{fii.get('net', 'N/A')} Cr ({fii.get('trend', '')})")
            lines.append(f"  DII: ₹{dii.get('net', 'N/A')} Cr ({dii.get('trend', '')})")
            net = (fii.get("net_value", 0) or 0) + (dii.get("net_value", 0) or 0)
            lines.append(f"  Net: {'🟢' if net > 0 else '🔴'} ₹{net:.0f} Cr")
        else:
            lines.append("  ℹ️ Check NSE website for today's FII/DII data")
            lines.append("  📌 nseindia.com/reports/fii-dii")
    except Exception:
        lines.append("  ℹ️ Check NSE website for today's FII/DII data")
    lines.append("")

    # 6. News Headlines
    lines.append("📰 TOP NEWS HEADLINES")
    lines.append("-" * 40)
    try:
        news = get_market_news_summary(limit=5)
        if news:
            for i, item in enumerate(news, 1):
                lines.append(f"  {i}. {item['title']}")
                lines.append(f"     Source: {item['source']}")

            sentiment = analyze_sentiment(news)
            lines.append(f"\n  📊 News Sentiment: {sentiment['overall_sentiment'].upper()}")
        else:
            lines.append("  ⚪ No news available")
    except Exception:
        lines.append("  ⚪ News fetch failed")

    lines.append("")

    # 7. Stock Screens
    lines.append("🔍 STOCK SCREENS")
    lines.append("-" * 40)

    try:
        fund_picks = run_screen("fundamental", universe[:20])
        if fund_picks:
            lines.append("  💎 Fundamentally Strong Stocks:")
            for p in fund_picks[:5]:
                lines.append(f"     {p['symbol']} (Score: {p['score']}/100, "
                           f"PE: {p.get('pe', 'N/A')}, ROCE: {p.get('roce', 'N/A')}%)")
    except Exception:
        lines.append("  ⚪ Screening unavailable")

    lines.append("")

    # 8. Investment Recommendations with Hypothesis
    lines.append("💡 INVESTMENT RECOMMENDATIONS")
    lines.append("-" * 40)

    try:
        recs = daily_screen_and_recommend(universe[:25], top_n=5)
        if recs:
            for i, rec in enumerate(recs, 1):
                verdict_icon = {
                    "STRONG BUY": "🔥",
                    "BUY": "✅",
                    "ACCUMULATE": "📈",
                    "HOLD": "⏸️",
                    "REDUCE": "⚠️",
                    "AVOID": "🚫",
                }.get(rec["verdict"], "•")

                lines.append(f"\n  {i}. {verdict_icon} {rec['symbol']} — {rec['verdict']} "
                           f"(Confidence: {rec['confidence']})")
                lines.append(f"     Price: ₹{_safe_get(rec, 'quote', 'price', default='N/A')}")

                hyp = rec.get("hypothesis", {})
                if hyp.get("technical"):
                    lines.append(f"     📊 {hyp['technical']}")
                if hyp.get("fundamental"):
                    lines.append(f"     📋 {hyp['fundamental']}")
                if hyp.get("valuation"):
                    lines.append(f"     💰 {hyp['valuation']}")
                if hyp.get("scenario"):
                    lines.append(f"     🔮 {hyp['scenario']}")
                if hyp.get("company_internals"):
                    lines.append(f"     🏢 {hyp['company_internals']}")

                risks = hyp.get("risks", [])
                if risks:
                    lines.append(f"     ⚠️ Risks: {'; '.join(risks[:2])}")

                if rec.get("risk_management") and isinstance(rec["risk_management"], str):
                    lines.append(f"     📏 Size: {rec['risk_management']}")

                lines.append("")
        else:
            lines.append("  No strong buy signals today. Market may be overvalued or uncertain.")
            lines.append("  Consider waiting for better entry points.")
    except Exception as e:
        lines.append(f"  ⚪ Recommendation engine error: {e}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("Generated by StockForge — Indian Stock Market Intelligence")
    lines.append("Disclaimer: This is for informational purposes only. Not investment advice.")
    lines.append("=" * 60)

    return "\n".join(lines)


def _safe_get(data: dict, *keys, default=None):
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


def save_briefing(content: str, date: str = None) -> str:
    """Save briefing to output file."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, f"daily_briefing_{date}.txt")
    with open(filepath, "w") as f:
        f.write(content)

    return filepath
