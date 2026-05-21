"""
StockForge Concall Analysis
Fetch conference call transcripts from screener.in, analyze for growth triggers,
and produce variant perception scorecards.
Adapted from samyakjain0606/awesome-stock-skills.
"""

import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConcallEntry:
    date: str
    title: str
    url: str
    transcript_url: Optional[str] = None


@dataclass
class GrowthTrigger:
    factor: str
    category: str  # "revenue", "margin", "capex", "management", "market"
    probability: str  # "high", "medium", "low"
    impact: str  # "high", "medium", "low"
    evidence: str


def fetch_concalls(symbol: str, exchange: str = "NSE") -> list[ConcallEntry]:
    """Fetch conference call links from screener.in."""
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    concalls = []

    # Look for conference call sections
    for link in soup.find_all("a", href=True):
        href = link.get("href", "").lower()
        text = link.get_text().strip().lower()
        if any(kw in text for kw in ["concall", "conference call", "earnings call"]):
            full_url = href if href.startswith("http") else f"https://www.screener.in{href}"
            date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", link.get_text())
            date = date_match.group(1) if date_match else "Unknown"
            concalls.append(ConcallEntry(
                date=date,
                title=link.get_text().strip(),
                url=full_url,
                transcript_url=full_url,
            ))

    # Also check BSE filings as fallback
    if not concalls:
        bse_url = f"https://www.bseindia.com/stock-share-price/{symbol}/"
        # BSE search requires different approach — skip for now
        pass

    return concalls


def analyze_concall_transcript(text: str) -> dict:
    """Analyze a concall transcript for key themes and growth triggers."""
    result = {
        "growth_triggers": [],
        "risk_factors": [],
        "management_tone": "neutral",
        "key_metrics_mentioned": {},
    }

    text_lower = text.lower()

    # Growth triggers
    growth_keywords = {
        "revenue": ["revenue growth", "topline", "sales growth", "revenue up", "record revenue"],
        "margin": ["margin expansion", "margin improvement", "ebitda margin", "operating leverage"],
        "capex": ["capex", "capacity expansion", "new plant", "new facility", "greenfield"],
        "market": ["market share", "new market", "geographic expansion", "export growth"],
        "product": ["new product", "product launch", "r&d", "innovation", "patent"],
        "order": ["order book", "order inflow", "pipeline", "deal wins"],
    }

    for category, keywords in growth_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                # Find context around the mention
                idx = text_lower.find(kw)
                context = text[max(0, idx - 50):idx + 100].strip()
                result["growth_triggers"].append(GrowthTrigger(
                    factor=kw,
                    category=category,
                    probability="high" if "record" in context or "significant" in context else "medium",
                    impact="high" if "margin" in category or "order" in category else "medium",
                    evidence=context[:100],
                ))

    # Risk factors
    risk_keywords = ["challenging", "headwind", "pressure", "decline", "loss", "risk",
                     "uncertainty", "regulatory", "competition", "slowdown"]
    for kw in risk_keywords:
        if kw in text_lower:
            idx = text_lower.find(kw)
            context = text[max(0, idx - 50):idx + 100].strip()
            result["risk_factors"].append(context[:150])

    # Management tone
    bullish_words = ["optimistic", "confident", "strong", "growth", "momentum", "outperform"]
    bearish_words = ["cautious", "uncertain", "challenging", "pressure", "concern"]
    bull_count = sum(1 for w in bullish_words if w in text_lower)
    bear_count = sum(1 for w in bearish_words if w in text_lower)

    if bull_count > bear_count + 2:
        result["management_tone"] = "bullish"
    elif bear_count > bull_count + 2:
        result["management_tone"] = "bearish"
    else:
        result["management_tone"] = "neutral"

    return result


def generate_vp_scorecard(symbol: str, concall_text: Optional[str] = None) -> str:
    """Generate a variant perception scorecard."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"📋 VARIANT PERCEPTION SCORECARD — {symbol}")
    lines.append("=" * 60)

    if concall_text:
        analysis = analyze_concall_transcript(concall_text)
        lines.append(f"\n📞 CONCALL ANALYSIS")
        lines.append("-" * 50)
        lines.append(f"  Management Tone: {analysis['management_tone'].upper()}")

        if analysis["growth_triggers"]:
            lines.append(f"\n  🚀 GROWTH TRIGGERS ({len(analysis['growth_triggers'])} found)")
            for t in analysis["growth_triggers"]:
                lines.append(f"    • [{t.probability.upper()} prob / {t.impact.upper()} impact] {t.factor}")
                lines.append(f"      Evidence: ...{t.evidence}...")

        if analysis["risk_factors"]:
            lines.append(f"\n  ⚠️ RISK FACTORS ({len(analysis['risk_factors'])} found)")
            for r in analysis["risk_factors"][:5]:
                lines.append(f"    • ...{r}...")
    else:
        lines.append(f"\n  No concall transcript provided.")
        lines.append(f"  Run: fetch_concalls('{symbol}') to get transcripts.")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
