"""
StockForge - Sentiment Analysis Module
Analyzes news sentiment, promoter activity, FII buying patterns.
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.news import get_stock_news, analyze_news_sentiment
from data.fii_dii import get_fii_dii_summary
from data.fundamentals import get_complete_fundamentals

logger = logging.getLogger(__name__)


def analyze_stock_sentiment(symbol: str) -> dict:
    """Analyze sentiment for a specific stock."""
    result = {
        "symbol": symbol.upper(),
        "news_sentiment": None,
        "fii_sentiment": None,
        "promoter_sentiment": None,
        "overall_sentiment": "neutral",
        "overall_score": 0,
    }

    try:
        # News sentiment
        news = get_stock_news(symbol, top_n=5)
        if news:
            news_sent = analyze_news_sentiment(news)
            result["news_sentiment"] = news_sent
            result["news_items"] = news[:3]  # Keep top 3 for reference

        # FII sentiment (market-level, as stock-level FII data needs NSE archives)
        fii_summary = get_fii_dii_summary(10)
        if "error" not in fii_summary:
            result["fii_sentiment"] = {
                "net_total_cr": fii_summary.get("fii_net_total_cr"),
                "trend": fii_summary.get("fii_trend"),
                "positive_days": fii_summary.get("fii_positive_days"),
                "total_days": fii_summary.get("trading_days"),
            }

        # Promoter sentiment (from holdings change)
        fund = get_complete_fundamentals(symbol)
        if fund.get("promoter_holding") is not None:
            ph = fund["promoter_holding"]
            result["promoter_sentiment"] = {
                "promoter_holding": ph,
                "assessment": "strong" if ph >= 50 else ("moderate" if ph >= 30 else "weak"),
            }
        if fund.get("pledge_percentage") is not None:
            result["promoter_sentiment"] = result.get("promoter_sentiment", {})
            result["promoter_sentiment"]["pledge"] = fund["pledge_percentage"]

        # Calculate overall sentiment score
        score = 0
        factors = 0

        # News score (-2 to +2)
        if result["news_sentiment"]:
            ns = result["news_sentiment"]
            if ns["sentiment"] == "bullish":
                score += 2
            elif ns["sentiment"] == "bearish":
                score -= 2
            factors += 1

        # FII score (-2 to +2)
        if result["fii_sentiment"]:
            fs = result["fii_sentiment"]
            if fs.get("trend") == "NET BUYER":
                score += 2
            elif fs.get("trend") == "NET SELLER":
                score -= 2
            factors += 1

        # Promoter score (-1 to +2)
        if result["promoter_sentiment"]:
            ps = result["promoter_sentiment"]
            if ps.get("assessment") == "strong":
                score += 2
            elif ps.get("assessment") == "moderate":
                score += 1
            elif ps.get("assessment") == "weak":
                score -= 1

            pledge = ps.get("pledge", 0)
            if pledge and pledge > 10:
                score -= 2
            elif pledge and pledge > 5:
                score -= 1

            factors += 1

        if factors > 0:
            result["overall_score"] = round(score / factors * 10, 1)

            if result["overall_score"] > 10:
                result["overall_sentiment"] = "very_bullish"
            elif result["overall_score"] > 5:
                result["overall_sentiment"] = "bullish"
            elif result["overall_score"] < -10:
                result["overall_sentiment"] = "very_bearish"
            elif result["overall_score"] < -5:
                result["overall_sentiment"] = "bearish"
            else:
                result["overall_sentiment"] = "neutral"

        return result

    except Exception as e:
        logger.error(f"Error analyzing sentiment for {symbol}: {e}")
        result["error"] = str(e)
        return result


def get_market_sentiment() -> dict:
    """Get overall market sentiment from news and FII flows."""
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "news_sentiment": None,
        "fii_summary": None,
        "overall": "neutral",
    }

    try:
        # Market news sentiment
        from data.news import get_market_news
        news = get_market_news(10)
        if news:
            result["news_sentiment"] = analyze_news_sentiment(news)
            result["news_items"] = news[:5]

        # FII flows
        fii = get_fii_dii_summary(10)
        if "error" not in fii:
            result["fii_summary"] = fii

        # Overall assessment
        score = 0
        if result["news_sentiment"]:
            if result["news_sentiment"]["sentiment"] == "bullish":
                score += 1
            elif result["news_sentiment"]["sentiment"] == "bearish":
                score -= 1

        if result["fii_summary"]:
            if result["fii_summary"].get("fii_trend") == "NET BUYER":
                score += 1
            elif result["fii_summary"].get("fii_trend") == "NET SELLER":
                score -= 1

        if score > 0:
            result["overall"] = "bullish"
        elif score < 0:
            result["overall"] = "bearish"

        return result

    except Exception as e:
        logger.error(f"Error computing market sentiment: {e}")
        result["error"] = str(e)
        return result


def format_sentiment_report(data: dict) -> str:
    """Format sentiment analysis into readable report."""
    lines = []
    lines.append(f"  SENTIMENT ANALYSIS - {data['symbol']}")
    lines.append(f"  {'─' * 45}")

    # News sentiment
    ns = data.get("news_sentiment")
    if ns:
        lines.append(f"  News Sentiment: {ns['sentiment'].upper()} (Score: {ns['score']:+d})")
        lines.append(f"    Positive: {ns['positive']} | Negative: {ns['negative']} | Neutral: {ns['neutral']}")

        # Show top news
        for item in data.get("news_items", [])[:3]:
            lines.append(f"    • {item['title']}")

    # FII sentiment
    fii = data.get("fii_sentiment")
    if fii:
        sign = "+" if fii.get("net_total_cr", 0) >= 0 else ""
        lines.append(f"  FII Trend (10d): {fii.get('trend', 'N/A')} (Net: {sign}₹{fii.get('net_total_cr', 0):.0f} Cr)")
        lines.append(f"    Positive days: {fii.get('positive_days', '?')}/{fii.get('total_days', '?')}")

    # Promoter sentiment
    ps = data.get("promoter_sentiment")
    if ps:
        lines.append(f"  Promoter Holding: {ps.get('promoter_holding', 'N/A')}% [{ps.get('assessment', 'N/A')}]")
        if ps.get("pledge") is not None:
            lines.append(f"  Pledge: {ps['pledge']}% {'⚠️ HIGH' if ps['pledge'] > 10 else '✓ OK'}")

    # Overall
    lines.append(f"")
    lines.append(f"  Overall Sentiment: {data['overall_sentiment'].upper()} (Score: {data['overall_score']:.1f})")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Sentiment Analysis Module Test ===\n")
    data = analyze_stock_sentiment("RELIANCE")
    print(format_sentiment_report(data))
