"""
StockForge Market Breadth Analyzer
Measures internal market health using advance/decline, stocks above MAs,
new highs/lows, sector participation, and VIX.
Adapted from ajeeshworkspace/indian-trading-skills.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BreadthReport:
    health_score: float  # 0-100
    regime: str  # "Risk-On", "Cautious", "Risk-Off"
    advance_decline_ratio: float
    above_200dma_pct: float
    new_highs_vs_lows: float
    sector_participation: float
    vix_signal: str
    recommendation: str


def analyze_breadth(
    advances: int = 0,
    declines: int = 0,
    unchanged: int = 0,
    above_200dma: int = 0,
    total_stocks: int = 500,
    new_52w_highs: int = 0,
    new_52w_lows: int = 0,
    sectors_advancing: int = 0,
    total_sectors: int = 13,
    vix: float = 15.0,
    nifty_change_pct: float = 0.0,
) -> BreadthReport:
    """Calculate market health score from breadth indicators."""

    # Component 1: Advance/Decline (25%)
    if advances + declines > 0:
        ad_ratio = advances / max(declines, 1)
        ad_score = min(100, (ad_ratio / 3.0) * 100)  # 3:1 = max score
    else:
        ad_ratio = 1.0
        ad_score = 50

    # Component 2: Stocks above 200 DMA (25%)
    above_200_pct = (above_200dma / total_stocks) * 100 if total_stocks > 0 else 50
    dma_score = above_200_pct

    # Component 3: New Highs vs Lows (20%)
    total_hl = new_52w_highs + new_52w_lows
    if total_hl > 0:
        hl_ratio = new_52w_highs / total_hl
        hl_score = hl_ratio * 100
    else:
        hl_ratio = 0.5
        hl_score = 50

    # Component 4: Sector Participation (15%)
    sector_pct = (sectors_advancing / total_sectors) * 100 if total_sectors > 0 else 50
    sector_score = sector_pct

    # Component 5: VIX Signal (15%)
    if vix < 12:
        vix_score = 80
        vix_signal = "LOW FEAR — complacent but bullish"
    elif vix < 18:
        vix_score = 65
        vix_signal = "MODERATE — normal market conditions"
    elif vix < 25:
        vix_score = 40
        vix_signal = "ELEVATED — increased caution warranted"
    elif vix < 35:
        vix_score = 20
        vix_signal = "HIGH FEAR — defensive positioning"
    else:
        vix_score = 10
        vix_signal = "PANIC — extreme fear, contrarian buy signal"

    # Composite score
    health = (
        ad_score * 0.25
        + dma_score * 0.25
        + hl_score * 0.20
        + sector_score * 0.15
        + vix_score * 0.15
    )

    # Regime classification
    if health >= 70:
        regime = "Risk-On"
        recommendation = "Add to positions. Market breadth confirms uptrend."
    elif health >= 45:
        regime = "Cautious"
        recommendation = "Selective buying. Avoid aggressive positioning."
    else:
        regime = "Risk-Off"
        recommendation = "Reduce exposure. Cash is a position. Wait for breadth improvement."

    # Override: if VIX is extreme, lower regime
    if vix > 30 and regime == "Risk-On":
        regime = "Cautious"
        recommendation = "Despite other signals, extreme VIX demands caution."

    return BreadthReport(
        health_score=round(health, 1),
        regime=regime,
        advance_decline_ratio=round(ad_ratio, 2),
        above_200dma_pct=round(above_200_pct, 1),
        new_highs_vs_lows=round(hl_ratio, 2),
        sector_participation=round(sector_pct, 1),
        vix_signal=vix_signal,
        recommendation=recommendation,
    )


def format_breadth_report(report: BreadthReport, nifty: Optional[float] = None) -> str:
    """Format breadth report."""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 MARKET BREADTH HEALTH REPORT")
    lines.append("=" * 60)
    if nifty:
        lines.append(f"  NIFTY 50: ₹{nifty:,.2f}")
    lines.append(f"  Health Score: {report.health_score:.0f}/100")

    # Regime emoji
    if report.regime == "Risk-On":
        emoji = "🟢"
    elif report.regime == "Cautious":
        emoji = "🟡"
    else:
        emoji = "🔴"

    lines.append(f"  Regime: {emoji} {report.regime.upper()}")

    lines.append(f"\n  COMPONENTS:")
    lines.append(f"    Advance/Decline Ratio: {report.advance_decline_ratio:.2f} (25%)")
    lines.append(f"    Stocks Above 200-DMA: {report.above_200dma_pct:.1f}% (25%)")
    lines.append(f"    New Highs vs Lows: {report.new_highs_vs_lows:.2f} (20%)")
    lines.append(f"    Sector Participation: {report.sector_participation:.1f}% (15%)")
    lines.append(f"    VIX Signal: {report.vix_signal} (15%)")

    lines.append(f"\n  💡 {report.recommendation}")
    lines.append(f"{'=' * 60}")
    return "\n".join(lines)
