"""
StockForge Scenario Analyzer
18-month probabilistic scenarios (Bull/Base/Bear) based on events,
macro factors, and historical patterns.
Adapted from ajeeshworkspace/indian-trading-skills.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Scenario:
    name: str  # "Bull", "Base", "Bear"
    probability: float  # percentage
    target_12m: float
    rationale: list
    key_drivers: list
    risks: list


# Historical pattern database
HISTORICAL_PATTERNS = {
    "rate_cut": {
        "impact": "Generally positive for rate-sensitive sectors (realty, auto, NBFCs). IT benefits from weaker rupee.",
        "avg_nifty_return_12m": 12.5,
        "sectors_benefit": ["realty", "auto", "nbfc", "it"],
        "sectors_hurt": ["banking"],  # NIM pressure
    },
    "rate_hike": {
        "impact": "Banks benefit from NIM expansion. Rate-sensitive sectors face headwinds.",
        "avg_nifty_return_12m": -3.2,
        "sectors_benefit": ["banking", "insurance"],
        "sectors_hurt": ["realty", "auto", "nbfc"],
    },
    "budget_bullish": {
        "impact": "Infrastructure capex push, tax cuts, PLI expansion.",
        "avg_nifty_return_12m": 10.8,
        "sectors_benefit": ["infra", "capital_goods", "defence", "railway"],
    },
    "crude_surge": {
        "impact": "Oil importing stocks hurt. OMCs, paints, tyres, airlines suffer. ONGC, Oil India benefit.",
        "avg_nifty_return_12m": -2.1,
        "sectors_benefit": ["ongc", "oil_india", "coal_india"],
        "sectors_hurt": ["paints", "tyres", "aviation", "omc"],
    },
    "monsoon_good": {
        "impact": "Rural demand boost. FMCG, tractors, fertilizers, two-wheelers benefit.",
        "avg_nifty_return_12m": 5.3,
        "sectors_benefit": ["fmcg", "auto", "fertilizer", "tractor"],
    },
    "election_uncertainty": {
        "impact": "VIX spikes, FII outflows, market volatility. Post-election clarity drives rerating.",
        "avg_nifty_return_12m": 8.1,
    },
    "global_risk_off": {
        "impact": "FII selling, rupee weakness, IT/pharma defensive outperformance.",
        "avg_nifty_return_12m": -8.5,
        "sectors_benefit": ["it", "pharma", "gold"],
        "sectors_hurt": ["fmcg", "banking", "infra"],
    },
    "china_slowdown": {
        "impact": "India manufacturing benefits (China+1). Specialty chemicals, electronics, auto ancillaries gain.",
        "avg_nifty_return_12m": 6.7,
        "sectors_benefit": ["specialty_chem", "electronics", "auto_ancillary"],
    },
}


def analyze_scenario(
    symbol: str,
    current_price: float,
    events: Optional[list[str]] = None,
    sector: Optional[str] = None,
    pe_ratio: Optional[float] = None,
) -> list[Scenario]:
    """Generate Bull/Base/Bear scenarios based on events and historical patterns."""
    scenarios = []

    # Base case: 12-15% annual return for quality stocks
    base_target = current_price * 1.13
    base_rationale = [
        "Conservative earnings growth of 12-15% CAGR",
        "Stable macro environment with moderate inflation",
        "Continued domestic institutional inflows (SIPs)",
    ]

    # Adjust for events
    if events:
        for event in events:
            event_lower = event.lower()
            for pattern_name, pattern in HISTORICAL_PATTERNS.items():
                if any(kw in event_lower for kw in pattern_name.split("_")):
                    base_rationale.append(f"Event impact: {pattern['impact'][:100]}")

    # Bull case: 25-35% upside
    bull_target = current_price * 1.30
    bull_rationale = [
        "Earnings beat expectations with margin expansion",
        "FII inflows resume, driving multiple expansion",
        "Favorable policy environment (rate cuts, reforms)",
        "Sector tailwinds from global shift (China+1, PLI)",
    ]
    bull_drivers = ["Multiple expansion (PE rerating)", "Earnings upgrade cycle", "FII/DII net buying"]
    bull_risks = ["Valuation stretch at upper end", "Global recession risk"]

    # Bear case: 15-25% downside
    bear_target = current_price * 0.80
    bear_rationale = [
        "Earnings disappointment or margin compression",
        "FII outflows due to global risk-off",
        "Rupee depreciation pressuring margins",
        "Regulatory or geopolitical shock",
    ]
    bear_drivers = ["Multiple compression", "Earnings downgrade", "FII selling"]
    bear_risks = ["Circuit limits may restrict downside", "Domestic buying provides floor"]

    # Sector-specific adjustments
    if sector:
        sector_lower = sector.lower()
        if "it" in sector_lower or "tech" in sector_lower:
            bull_rationale.append("USD strength benefits IT revenue")
            bear_rationale.append("US recession risk reduces IT spending")
        elif "bank" in sector_lower:
            bull_rationale.append("Credit growth + stable NIMs drive earnings")
            bear_rationale.append("NPA cycle or rate cut pressure on margins")
        elif "fmcg" in sector_lower:
            bull_rationale.append("Rural demand recovery, margin expansion")
            bear_rationale.append("Input cost inflation, volume stagnation")

    # PE-based valuation check
    if pe_ratio:
        if pe_ratio > 60:
            bear_target = current_price * 0.70  # Higher downside for overvalued
            bull_risks.append("High PE multiple vulnerable to compression")
        elif pe_ratio < 15:
            bull_target = current_price * 1.45  # Higher upside for undervalued
            bull_rationale.append("Undervalued at current PE — rerating potential")

    scenarios = [
        Scenario("Bull", 25, bull_target, bull_rationale, bull_drivers, bull_risks),
        Scenario("Base", 50, base_target, base_rationale, ["Steady execution", "Status quo"], ["Execution misses"]),
        Scenario("Bear", 25, bear_target, bear_rationale, bear_drivers, bear_risks),
    ]

    return scenarios


def format_scenario_report(
    symbol: str,
    current_price: float,
    scenarios: list[Scenario],
) -> str:
    """Format scenarios into readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"🔮 18-MONTH SCENARIO ANALYSIS — {symbol}")
    lines.append("=" * 60)
    lines.append(f"  Current Price: ₹{current_price:.2f}")
    lines.append(f"\n  Expected Return (prob-weighted): ", end="")

    weighted = sum(s.probability / 100 * ((s.target_12m / current_price) - 1) * 100 for s in scenarios)
    lines[-1] += f"{weighted:+.1f}%"

    for s in scenarios:
        lines.append(f"\n{'─' * 50}")
        lines.append(f"  🟢 {s.name.upper()} SCENARIO ({s.probability}% probability)")
        lines.append(f"  Target: ₹{s.target_12m:.2f} ({((s.target_12m/current_price)-1)*100:+.1f}%)")
        lines.append(f"\n  Rationale:")
        for r in s.rationale:
            lines.append(f"    • {r}")
        if s.key_drivers:
            lines.append(f"\n  Key Drivers: {'; '.join(s.key_drivers)}")
        lines.append(f"\n  Key Risks: {'; '.join(s.risks)}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
