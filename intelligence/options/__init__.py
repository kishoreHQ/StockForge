"""
StockForge Options Strategy Advisor
Simplified Black-Scholes pricing, Greeks calculation, and strategy builders.
Adapted from ajeeshworkspace/indian-trading-skills.
"""

import math
from dataclasses import dataclass


@dataclass
class OptionGreeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    price: float
    iv: float


def norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)


def norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes(
    spot: float,
    strike: float,
    days_to_expiry: float,
    volatility: float,
    risk_free_rate: float = 0.065,
    option_type: str = "call",
) -> OptionGreeks:
    """Calculate Black-Scholes option price and Greeks."""
    T = days_to_expiry / 365.0
    if T <= 0:
        # Expired option
        intrinsic = max(0, spot - strike) if option_type == "call" else max(0, strike - spot)
        return OptionGreeks(
            delta=1.0 if (option_type == "call" and spot > strike) else 0.0,
            gamma=0, theta=0, vega=0, rho=0,
            price=intrinsic, iv=volatility,
        )

    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * T) / (volatility * math.sqrt(T))
    d2 = d1 - volatility * math.sqrt(T)

    if option_type == "call":
        price = spot * norm_cdf(d1) - strike * math.exp(-risk_free_rate * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        rho = strike * T * math.exp(-risk_free_rate * T) * norm_cdf(d2) / 100
    else:
        price = strike * math.exp(-risk_free_rate * T) * norm_cdf(-d2) - spot * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1
        rho = -strike * T * math.exp(-risk_free_rate * T) * norm_cdf(-d2) / 100

    gamma = norm_pdf(d1) / (spot * volatility * math.sqrt(T))
    theta = (-(spot * norm_pdf(d1) * volatility) / (2 * math.sqrt(T))
             - risk_free_rate * strike * math.exp(-risk_free_rate * T) * norm_cdf(d2 if option_type == "call" else -d2)) / 365
    vega = spot * norm_pdf(d1) * math.sqrt(T) / 100

    return OptionGreeks(
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta=round(theta, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
        price=round(price, 2),
        iv=volatility,
    )


def find_implied_volatility(
    spot: float,
    strike: float,
    days_to_expiry: float,
    market_price: float,
    option_type: str = "call",
    risk_free_rate: float = 0.065,
    max_iterations: int = 50,
    tolerance: float = 0.001,
) -> float:
    """Newton-Raphson IV solver."""
    vol = 0.3  # initial guess
    for _ in range(max_iterations):
        greeks = black_scholes(spot, strike, days_to_expiry, vol, risk_free_rate, option_type)
        diff = greeks.price - market_price
        if abs(diff) < tolerance:
            return round(vol, 4)
        vega = greeks.vega * 100  # un-normalize
        if vega == 0:
            break
        vol = vol - diff / vega
        vol = max(0.01, min(vol, 5.0))  # clamp
    return round(vol, 4)


# Strategy definitions
STRATEGIES = {
    "covered_call": {
        "name": "Covered Call",
        "description": "Own stock + sell OTM call. Income generation with limited upside.",
        "max_profit": "Premium received + (strike - spot) if ITM",
        "max_loss": "Spot - premium (if stock goes to zero)",
        "best_when": "Neutral to slightly bullish, low volatility",
    },
    "protective_put": {
        "name": "Protective Put",
        "description": "Own stock + buy put. Insurance against downside.",
        "max_profit": "Unlimited (stock upside)",
        "max_loss": "Spot - strike + premium paid",
        "best_when": "Bullish but want downside protection",
    },
    "bull_call_spread": {
        "name": "Bull Call Spread",
        "description": "Buy ATM call + sell OTM call. Defined risk bullish.",
        "max_profit": "Spread width - net debit",
        "max_loss": "Net debit paid",
        "best_when": "Moderately bullish, want to reduce cost",
    },
    "bear_put_spread": {
        "name": "Bear Put Spread",
        "description": "Buy ATM put + sell OTM put. Defined risk bearish.",
        "max_profit": "Spread width - net debit",
        "max_loss": "Net debit paid",
        "best_when": "Moderately bearish",
    },
    "iron_condor": {
        "name": "Iron Condor",
        "description": "Sell OTM call spread + sell OTM put spread. Range-bound strategy.",
        "max_profit": "Net premium received",
        "max_loss": "Spread width - premium",
        "best_when": "Low volatility, range-bound market",
    },
    "straddle": {
        "name": "Long Straddle",
        "description": "Buy ATM call + buy ATM put. Profits on big move either way.",
        "max_profit": "Unlimited (big move in either direction)",
        "max_loss": "Total premium paid",
        "best_when": "Expect big move (earnings, events), high IV expected",
    },
    "strangle": {
        "name": "Long Strangle",
        "description": "Buy OTM call + buy OTM put. Cheaper than straddle, needs bigger move.",
        "max_profit": "Unlimited",
        "max_loss": "Total premium paid",
        "best_when": "Expect very big move, IV is low",
    },
    "iron_butterfly": {
        "name": "Iron Butterfly",
        "description": "Sell ATM straddle + buy OTM wings. Max profit at the money.",
        "max_profit": "Net premium received",
        "max_loss": "Spread width - premium",
        "best_when": "Expect price to stay at ATM, IV crush",
    },
}


def format_options_report(
    spot: float,
    strategy_name: str,
    strikes: list,
    days_to_expiry: float,
    volatility: float,
) -> str:
    """Format options strategy analysis."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"📈 OPTIONS STRATEGY — {strategy_name.upper()}")
    lines.append("=" * 60)
    lines.append(f"  Spot: ₹{spot:.2f} | DTE: {days_to_expiry:.0f} | IV: {volatility*100:.1f}%")

    strategy = STRATEGIES.get(strategy_name, {})
    if strategy:
        lines.append(f"\n  Strategy: {strategy.get('name', strategy_name)}")
        lines.append(f"  Description: {strategy.get('description', '')}")
        lines.append(f"  Best When: {strategy.get('best_when', '')}")
        lines.append(f"  Max Profit: {strategy.get('max_profit', '')}")
        lines.append(f"  Max Loss: {strategy.get('max_loss', '')}")

    # Calculate Greeks for each strike
    lines.append(f"\n  GREEKS BY STRIKE:")
    lines.append(f"  {'Strike':>10} {'Type':>6} {'Price':>8} {'Delta':>8} {'Gamma':>8} {'Theta':>8} {'Vega':>8}")
    lines.append(f"  {'─' * 60}")

    for strike in strikes:
        for opt_type in ["call", "put"]:
            g = black_scholes(spot, strike, days_to_expiry, volatility, option_type=opt_type)
            lines.append(f"  {strike:>10.0f} {opt_type:>6} {g.price:>8.2f} {g.delta:>8.4f} {g.gamma:>8.6f} {g.theta:>8.4f} {g.vega:>8.4f}")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)
