"""StockForge Intelligence - Full stock analysis report."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_quote, get_history
from analysis.technical import full_technical_analysis
from analysis.fundamental import score_fundamentals
from analysis.valuation import dcf_estimate, pe_pb_analysis
from data.news import get_moneycontrol_news, analyze_sentiment
from intelligence.recommendation_engine import generate_recommendation
from datetime import datetime


def generate_stock_report(symbol: str) -> str:
    """Generate comprehensive analysis report for a single stock."""
    lines = []
    
    lines.append("=" * 60)
    lines.append(f"📋 STOCK ANALYSIS REPORT: {symbol.upper()}")
    lines.append(f"   {datetime.now().strftime('%A, %d %B %Y, %H:%M IST')}")
    lines.append("=" * 60)
    lines.append("")
    
    # Quote
    quote = get_quote(symbol)
    if "error" in quote:
        return f"❌ Error: {quote['error']}"
    
    lines.append("💵 CURRENT QUOTE")
    lines.append("-" * 40)
    lines.append(f"  Price:        ₹{quote['price']}")
    lines.append(f"  Change:       {quote['change']:+.2f} ({quote['change_pct']:+.2f}%)")
    lines.append(f"  Day Range:    ₹{quote['low']} - ₹{quote['high']}")
    lines.append(f"  52W Range:    ₹{quote['52w_low']} - ₹{quote['52w_high']}")
    lines.append(f"  Volume:       {quote['volume']:,}")
    if quote.get("market_cap"):
        cap = quote["market_cap"]
        if cap > 1e12:
            lines.append(f"  Market Cap:   ₹{cap/1e12:.2f} Lakh Cr")
        elif cap > 1e10:
            lines.append(f"  Market Cap:   ₹{cap/1e10:.2f} Thousand Cr")
        else:
            lines.append(f"  Market Cap:   ₹{cap/1e7:.0f} Cr")
    if quote.get("pe_ratio"):
        lines.append(f"  PE Ratio:     {quote['pe_ratio']:.1f}")
    lines.append("")
    
    # Technical Analysis
    tech = full_technical_analysis(symbol)
    if "error" not in tech:
        lines.append("📊 TECHNICAL ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"  Rating:       {tech.get('rating', 'N/A')}")
        lines.append(f"  RSI (14):     {tech.get('rsi_14', 'N/A')}")
        
        macd = tech.get("macd", {})
        lines.append(f"  MACD:         {macd.get('macd', 'N/A')} ({macd.get('trend', '')})")
        
        bb = tech.get("bollinger", {})
        lines.append(f"  Bollinger:    {bb.get('signal', 'N/A')}")
        lines.append(f"  Upper: ₹{bb.get('upper', 'N/A')}, "
                    f"Middle: ₹{bb.get('middle', 'N/A')}, "
                    f"Lower: ₹{bb.get('lower', 'N/A')}")
        
        ma = tech.get("moving_averages", {})
        lines.append(f"  SMA 20:       ₹{ma.get('sma_20', 'N/A')} "
                    f"{'✅ Above' if ma.get('above_sma_20') else '🔴 Below'}")
        lines.append(f"  SMA 50:       ₹{ma.get('sma_50', 'N/A')} "
                    f"{'✅ Above' if ma.get('above_sma_50') else '🔴 Below'}")
        lines.append(f"  SMA 200:      ₹{ma.get('sma_200', 'N/A')} "
                    f"{'✅ Above' if ma.get('above_sma_200') else '🔴 Below'}")
        
        if ma.get("golden_cross"):
            lines.append(f"  Golden Cross: ✅ Yes")
        
        sr = tech.get("support_resistance", {})
        if sr.get("resistance"):
            lines.append(f"  Resistance:   ₹{', ₹'.join(str(r) for r in sr['resistance'][:2])}")
        if sr.get("support"):
            lines.append(f"  Support:      ₹{', ₹'.join(str(s) for s in sr['support'][:2])}")
        
        vol = tech.get("volume", {})
        lines.append(f"  Volume:       {vol.get('signal', 'N/A')} "
                    f"(Ratio: {vol.get('ratio', 'N/A')}x avg)")
        
        lines.append(f"\n  Signals:")
        for sig in tech.get("signals", []):
            lines.append(f"    {sig}")
        lines.append("")
    
    # Fundamental Analysis
    fund = score_fundamentals(symbol)
    if "error" not in fund:
        lines.append("📋 FUNDAMENTAL ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"  Score:        {fund['score']}/100 ({fund['tier']})")
        
        ratios = fund.get("ratios", {})
        lines.append(f"  PE:           {ratios.get('pe', 'N/A')}")
        lines.append(f"  PB:           {ratios.get('pb', 'N/A')}")
        lines.append(f"  ROCE:         {ratios.get('roce', 'N/A')}%")
        lines.append(f"  ROE:          {ratios.get('roe', 'N/A')}%")
        lines.append(f"  Debt/Equity:  {ratios.get('debt_to_equity', 'N/A')}")
        lines.append(f"  Profit Margin:{ratios.get('profit_margin', 'N/A')}%")
        lines.append(f"  Dividend Yield:{ratios.get('dividend_yield', 'N/A')}%")
        
        lines.append(f"\n  Strengths:")
        for sig in fund.get("signals", []):
            lines.append(f"    ✅ {sig}")
        
        if fund.get("risks"):
            lines.append(f"\n  Concerns:")
            for risk in fund.get("risks", []):
                lines.append(f"    ⚠️ {risk}")
        lines.append("")
    
    # Valuation
    val = dcf_estimate(symbol)
    if "error" not in val:
        lines.append("💰 VALUATION (DCF)")
        lines.append("-" * 40)
        lines.append(f"  Intrinsic Value: ₹{val['intrinsic_value']}")
        lines.append(f"  Current Price:   ₹{val['current_price']}")
        lines.append(f"  Upside/Downside: {val['upside_pct']:+.1f}%")
        lines.append(f"  Verdict:         {val['verdict']}")
        lines.append(f"  Assumptions: Growth {val['assumptions']['growth_rate_pct']}%, "
                    f"Discount {val['assumptions']['discount_rate_pct']}%")
        lines.append("")
    
    # Recommendation
    rec = generate_recommendation(symbol)
    lines.append("💡 INVESTMENT RECOMMENDATION")
    lines.append("-" * 40)
    
    verdict_icons = {
        "STRONG BUY": "🔥", "BUY": "✅", "ACCUMULATE": "📈",
        "HOLD": "⏸️", "REDUCE": "⚠️", "AVOID": "🚫",
    }
    icon = verdict_icons.get(rec.get("verdict", ""), "•")
    lines.append(f"  Verdict:      {icon} {rec.get('verdict', 'N/A')}")
    lines.append(f"  Confidence:   {rec.get('confidence', 0)}")
    
    hyp = rec.get("hypothesis", {})
    if hyp.get("technical"):
        lines.append(f"  Technical:    {hyp['technical']}")
    if hyp.get("fundamental"):
        lines.append(f"  Fundamental:  {hyp['fundamental']}")
    if hyp.get("valuation"):
        lines.append(f"  Valuation:    {hyp['valuation']}")
    
    risks = hyp.get("risks", [])
    if risks:
        lines.append(f"\n  Key Risks:")
        for r in risks[:3]:
            lines.append(f"    ⚠️ {r}")
    
    lines.append("")
    
    # News
    lines.append("📰 RECENT NEWS")
    lines.append("-" * 40)
    try:
        news = get_moneycontrol_news(symbol.upper(), limit=3)
        if news:
            for i, item in enumerate(news[:3], 1):
                lines.append(f"  {i}. {item['title']}")
        else:
            lines.append("  No recent news found")
    except Exception:
        lines.append("  News fetch failed")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("Disclaimer: This is for informational purposes only. Not investment advice.")
    lines.append("=" * 60)
    
    return "\n".join(lines)
