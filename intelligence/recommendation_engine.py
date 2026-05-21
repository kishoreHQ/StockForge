"""StockForge Intelligence - Recommendation engine with full hypothesis framework.

Includes: news, company internals, technical, valuation, scenarios, risk management,
concall triggers. Similar to ContentForge's intelligence pipeline.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_quote, get_history
from analysis.technical import full_technical_analysis
from analysis.fundamental import score_fundamentals
from analysis.valuation import dcf_estimate, pe_pb_analysis
from data.news import get_market_news_summary, analyze_sentiment
from data.fundamentals import get_shareholding
from data.macro import get_india_vix
from intelligence.scenarios import analyze_scenario, format_scenario_report
from intelligence.concalls import fetch_concalls, generate_vp_scorecard
from intelligence.breadth import analyze_breadth
from risk import generate_risk_report
import json
from datetime import datetime


def _safe_get(data: dict, *keys, default=None):
    """Safely navigate nested dicts."""
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


def generate_recommendation(
    symbol: str,
    account_size: float = 500000,
    risk_pct: float = 2.0,
) -> dict:
    """Generate investment recommendation with full hypothesis framework."""
    rec = {
        "symbol": symbol.upper(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().strftime("%H:%M IST"),
    }

    # 1. Quote
    quote = get_quote(symbol)
    rec["quote"] = quote
    price = _safe_get(quote, "price", default=0)
    if not price:
        return {**rec, "verdict": "SKIP", "confidence": 0, "hypothesis": {"error": "No price data"}}

    # 2. Technical analysis
    tech = full_technical_analysis(symbol)
    rec["technical"] = tech

    # 3. Fundamental scoring
    fund = score_fundamentals(symbol)
    rec["fundamental"] = fund

    # 4. Valuation
    val = dcf_estimate(symbol)
    rec["valuation"] = val

    # 5. Shareholding
    sh = get_shareholding(symbol)
    rec["shareholding"] = sh

    # 6. News sentiment
    try:
        news = get_market_news_summary(limit=3, keyword=symbol)
        if news:
            sentiment = analyze_sentiment(news)
            rec["news"] = {
                "headlines": [n["title"] for n in news[:3]],
                "sentiment": sentiment.get("overall_sentiment", "neutral"),
                "sentiment_score": sentiment.get("score", 0),
            }
        else:
            rec["news"] = {"sentiment": "neutral", "headlines": []}
    except Exception:
        rec["news"] = {"sentiment": "neutral", "headlines": [], "error": "Fetch failed"}

    # Synthesize hypothesis
    confidence = 0
    hypothesis = {
        "news_sentiment": "",
        "company_internals": "",
        "technical": "",
        "fundamental": "",
        "valuation": "",
        "scenario": "",
        "risks": [],
        "catalysts": [],
    }

    # ── News Hypothesis ──
    news_sentiment = _safe_get(rec, "news", "sentiment", default="neutral")
    news_score = _safe_get(rec, "news", "sentiment_score", default=0)
    if news_sentiment == "positive":
        confidence += 10
        hypothesis["news_sentiment"] = f"Positive news flow — sentiment score {news_score:+.1f}"
        hypothesis["catalysts"].append("Favorable news coverage")
    elif news_sentiment == "negative":
        confidence -= 10
        hypothesis["news_sentiment"] = f"Negative news flow — sentiment score {news_score:+.1f}"
        hypothesis["risks"].append("Adverse news sentiment")

    # ── Company Internals Hypothesis ──
    promoter = _safe_get(sh, "promoter", default=0)
    promoter_pledge = _safe_get(sh, "promoter_pledge", default=0)
    fii = _safe_get(sh, "fii", default=0)
    dii = _safe_get(sh, "dii", default=0)

    internals_parts = []
    if promoter > 50:
        internals_parts.append(f"Strong promoter holding ({promoter}%)")
        confidence += 5
    elif promoter < 25:
        internals_parts.append(f"Low promoter holding ({promoter}%)")
        hypothesis["risks"].append(f"Low promoter stake ({promoter}%)")

    if promoter_pledge > 0:
        internals_parts.append(f"⚠️ Promoter pledge: {promoter_pledge}%")
        hypothesis["risks"].append(f"Promoter pledge risk ({promoter_pledge}%)")
        confidence -= 5

    if fii > 20:
        internals_parts.append(f"Strong FII interest ({fii}%)")
    if dii > 20:
        internals_parts.append(f"Strong DII support ({dii}%)")

    hypothesis["company_internals"] = "; ".join(internals_parts) if internals_parts else "Limited promoter/FII data"

    # ── Technical Hypothesis ──
    if "signals" in tech:
        bullish_signals = [s for s in tech["signals"] if "✅" in s or "📈" in s or "BULL" in s.upper()]
        bearish_signals = [s for s in tech["signals"] if "⚠️" in s or "📉" in s or "BEAR" in s.upper()]

        if len(bullish_signals) > len(bearish_signals):
            confidence += 15
            hypothesis["technical"] = f"Technically bullish: {', '.join(bullish_signals[:2])}"
        elif bearish_signals:
            confidence -= 10
            hypothesis["technical"] = f"Technical concerns: {', '.join(bearish_signals[:2])}"
        else:
            hypothesis["technical"] = "Mixed signals — neutral technical setup"

    # ── Fundamental Hypothesis ──
    score = _safe_get(fund, "score", default=0)
    if score >= 70:
        confidence += 20
        hypothesis["fundamental"] = f"Strong fundamentals (Score: {score}/100, {fund.get('tier', 'N/A')})"
    elif score >= 50:
        confidence += 5
        hypothesis["fundamental"] = f"Average fundamentals (Score: {score}/100, {fund.get('tier', 'N/A')})"
    else:
        confidence -= 15
        hypothesis["fundamental"] = f"Weak fundamentals (Score: {score}/100, {fund.get('tier', 'N/A')})"
        for r in fund.get("risks", [])[:3]:
            if r not in hypothesis["risks"]:
                hypothesis["risks"].append(r)

    # ── Valuation Hypothesis ──
    verdict_val = _safe_get(val, "verdict", default="FAIR")
    intrinsic = _safe_get(val, "intrinsic_value", default=price)
    upside = _safe_get(val, "upside_pct", default=0)

    if verdict_val == "UNDERVALUED":
        confidence += 15
        hypothesis["valuation"] = f"Undervalued: {upside}% upside to ₹{intrinsic} (DCF intrinsic)"
        hypothesis["catalysts"].append("Valuation rerating potential")
    elif verdict_val == "OVERVALUED":
        confidence -= 10
        hypothesis["valuation"] = f"Overvalued: {abs(upside)}% downside from current levels"
        hypothesis["risks"].append("Valuation stretch")
    else:
        confidence += 5
        hypothesis["valuation"] = "Fairly valued — entry on dips"

    # PE check
    pe = _safe_get(quote, "pe_ratio", default=0)
    if isinstance(pe, (int, float)) and pe > 60:
        hypothesis["risks"].append(f"High PE ({pe}) — vulnerable to earnings miss")
        confidence -= 5

    # ── Scenario Analysis ──
    try:
        sector = _safe_get(fund, "sector", default=None)
        scenarios = analyze_scenario(
            symbol=symbol.upper(),
            current_price=price,
            events=None,
            sector=sector,
            pe_ratio=pe if isinstance(pe, (int, float)) else None,
        )
        weighted_return = sum(
            s.probability / 100 * ((s.target_12m / price) - 1) * 100
            for s in scenarios
        )
        hypothesis["scenario"] = (
            f"12M expected: {weighted_return:+.1f}% | "
            f"Bull: ₹{scenarios[0].target_12m:.0f} ({((scenarios[0].target_12m/price)-1)*100:+.0f}%) | "
            f"Bear: ₹{scenarios[2].target_12m:.0f} ({((scenarios[2].target_12m/price)-1)*100:+.0f}%)"
        )
        if weighted_return > 15:
            confidence += 10
        elif weighted_return < -5:
            confidence -= 10
    except Exception:
        hypothesis["scenario"] = "Scenario analysis unavailable"

    # ── VIX Context ──
    try:
        vix = get_india_vix()
        if "vix" in vix:
            vix_val = vix["vix"]
            if vix_val > 25:
                hypothesis["risks"].append(f"High VIX ({vix_val}) — market stress")
                confidence -= 5
    except Exception:
        pass

    # Deduplicate risks
    hypothesis["risks"] = list(dict.fromkeys(hypothesis["risks"]))[:6]

    # Final verdict
    if confidence >= 35:
        verdict = "STRONG BUY"
    elif confidence >= 20:
        verdict = "BUY"
    elif confidence >= 5:
        verdict = "ACCUMULATE"
    elif confidence >= -10:
        verdict = "HOLD"
    elif confidence >= -25:
        verdict = "REDUCE"
    else:
        verdict = "AVOID"

    rec["confidence"] = confidence
    rec["verdict"] = verdict
    rec["hypothesis"] = hypothesis

    # ── Risk Management ──
    try:
        # Auto-calculate stop-loss at 2x ATR or 5% below, whichever is lower
        atr = _safe_get(tech, "atr", default=price * 0.02)
        atr_sl = price - (atr * 2)
        pct_sl = price * 0.95
        sl_price = max(atr_sl, pct_sl)

        # Target: DCF intrinsic or 20% above, whichever is higher
        target = max(intrinsic if isinstance(intrinsic, (int, float)) else price * 1.2, price * 1.2)

        risk_report = generate_risk_report(
            account_size=account_size,
            entry_price=price,
            stop_loss_price=round(sl_price, 2),
            target_price=round(target, 2),
            atr=atr if isinstance(atr, (int, float)) else None,
            support_level=None,
            win_rate=None,
            risk_pct=risk_pct,
        )
        rec["risk_management"] = risk_report
    except Exception:
        rec["risk_management"] = "Risk analysis unavailable"

    return rec


def format_stock_report(rec: dict) -> str:
    """Format full stock report with hypothesis."""
    lines = []
    q = rec.get("quote", {})
    price = _safe_get(q, "price", default=0)
    symbol = rec.get("symbol", "UNKNOWN")

    lines.append("=" * 65)
    lines.append(f"📊 STOCKFORGE ANALYSIS — {symbol}")
    lines.append(f"   {rec.get('date', '')} | {rec.get('timestamp', '')}")
    lines.append("=" * 65)

    if price:
        chg = _safe_get(q, "change", default=0)
        chg_pct = _safe_get(q, "change_pct", default=0)
        arrow = "🟢" if chg >= 0 else "🔴"
        lines.append(f"\n  💲 Price: ₹{price:.2f} {arrow} ({chg:+.2f}, {chg_pct:+.2f}%)")

    # Verdict
    verdict_icon = {
        "STRONG BUY": "🔥", "BUY": "✅", "ACCUMULATE": "📈",
        "HOLD": "⏸️", "REDUCE": "⚠️", "AVOID": "🚫",
    }.get(rec.get("verdict", ""), "•")
    lines.append(f"  {verdict_icon} Verdict: {rec.get('verdict', 'N/A')} (Confidence: {rec.get('confidence', 0)})")

    # ── HYPOTHESIS SECTION ──
    hyp = rec.get("hypothesis", {})
    if hyp and "error" not in hyp:
        lines.append(f"\n{'─' * 65}")
        lines.append("  🧠 INVESTMENT HYPOTHESIS")
        lines.append(f"{'─' * 65}")

        if hyp.get("news_sentiment"):
            lines.append(f"\n  📰 NEWS SENTIMENT:")
            lines.append(f"    {hyp['news_sentiment']}")

        if hyp.get("company_internals"):
            lines.append(f"\n  🏢 COMPANY INTERNALS:")
            lines.append(f"    {hyp['company_internals']}")

        if hyp.get("technical"):
            lines.append(f"\n  📊 TECHNICAL:")
            lines.append(f"    {hyp['technical']}")

        if hyp.get("fundamental"):
            lines.append(f"\n  📋 FUNDAMENTAL:")
            lines.append(f"    {hyp['fundamental']}")

        if hyp.get("valuation"):
            lines.append(f"\n  💰 VALUATION:")
            lines.append(f"    {hyp['valuation']}")

        if hyp.get("scenario"):
            lines.append(f"\n  🔮 12-MONTH SCENARIO:")
            lines.append(f"    {hyp['scenario']}")

        if hyp.get("catalysts"):
            lines.append(f"\n  🚀 CATALYSTS:")
            for c in hyp["catalysts"]:
                lines.append(f"    • {c}")

        if hyp.get("risks"):
            lines.append(f"\n  ⚠️ RISKS:")
            for r in hyp["risks"]:
                lines.append(f"    • {r}")

    # Risk management
    risk_data = rec.get("risk_management", "")
    if isinstance(risk_data, str) and risk_data != "Risk analysis unavailable":
        lines.append(f"\n{risk_data}")

    lines.append(f"\n{'=' * 65}")
    lines.append("  Disclaimer: For informational purposes only. Not investment advice.")
    lines.append(f"{'=' * 65}")

    return "\n".join(lines)


def daily_screen_and_recommend(
    universe: list = None,
    top_n: int = 5,
    account_size: float = 500000,
    risk_pct: float = 2.0,
) -> list:
    """Screen universe and return top N investment recommendations."""
    if universe is None:
        from data.market_data import get_index_constituents
        universe = get_index_constituents("nifty50")[:30]

    all_recs = []
    for symbol in universe:
        try:
            rec = generate_recommendation(symbol, account_size, risk_pct)
            all_recs.append(rec)
        except Exception:
            continue

    # Sort by confidence, return buys first
    buys = [r for r in all_recs if r.get("verdict") in ("STRONG BUY", "BUY", "ACCUMULATE")]
    buys.sort(key=lambda x: x["confidence"], reverse=True)
    return buys[:top_n]
