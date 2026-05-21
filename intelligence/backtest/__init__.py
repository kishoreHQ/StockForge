"""
StockForge Backtest Validator
Validates trading strategy backtests with India-specific cost modeling.
Adapted from ajeeshworkspace/indian-trading-skills.
"""

from dataclasses import dataclass


@dataclass
class BacktestResult:
    score: int  # 0-100
    verdict: str  # "Deploy", "Refine", "Abandon"
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    red_flags: list
    recommendations: list


# India-specific costs
COSTS = {
    "delivery": {
        "stt": 0.001,       # 0.1% on sell side
        "stamp_duty": 0.00015,  # 0.015% on buy
        "etf_charges": 0.0000345,
        "sebi_fees": 0.000001,
        "gst_rate": 0.18,
        "brokerage_rate": 0.0003,  # discount broker
    },
    "intraday": {
        "stt": 0.00025,
        "stamp_duty": 0.00003,
        "etf_charges": 0.0000345,
        "sebi_fees": 0.000001,
        "gst_rate": 0.18,
        "brokerage_rate": 0.0003,
    },
    "fno": {
        "stt": 0.000625,  # sell side only
        "stamp_duty": 0.00003,
        "etf_charges": 0.0000345,
        "sebi_fees": 0.000001,
        "gst_rate": 0.18,
        "brokerage_rate": 0.0003,
    },
}


def calculate_total_cost(trade_value: float, segment: str = "delivery") -> float:
    """Calculate all-in trading cost for Indian market."""
    c = COSTS.get(segment, COSTS["delivery"])
    brokerage = trade_value * c["brokerage_rate"]
    stt = trade_value * c["stt"]
    stamp = trade_value * c["stamp_duty"]
    exchange = trade_value * c["etf_charges"]
    sebi = trade_value * c["sebi_fees"]
    subtotal = brokerage + stt + stamp + exchange + sebi
    gst = subtotal * c["gst_rate"]
    return subtotal + gst


def evaluate_backtest(
    trades: int,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    max_drawdown: float,
    years: float,
    parameters: int = 5,
    slippage_modeled: bool = False,
    segment: str = "delivery",
    capital: float = 500000,
) -> BacktestResult:
    """Evaluate a backtest with India-specific cost modeling."""
    red_flags = []
    recommendations = []

    # Calculate profit factor
    wins = trades * (win_rate / 100.0)
    losses = trades * (1 - win_rate / 100.0)
    gross_profit = wins * avg_win
    gross_loss = losses * avg_loss
    profit_factor = gross_profit / max(gross_loss, 0.01)

    # Estimate costs
    avg_trade_value = capital * 0.1  # 10% of capital per trade
    cost_per_trade = calculate_total_cost(avg_trade_value, segment)
    total_costs = trades * cost_per_trade
    net_profit = gross_profit - gross_loss - total_costs

    # CAGR
    total_return = net_profit / capital if capital > 0 else 0
    cagr = ((1 + total_return) ** (1 / max(years, 1)) - 1) * 100

    # Sharpe approximation
    sharpe = cagr / max(max_drawdown, 1) if max_drawdown > 0 else 0

    # Calmar ratio
    calmar = cagr / max(max_drawdown, 1)

    # Scoring (0-100)
    score = 0

    # Win rate (20 pts)
    if win_rate >= 60:
        score += 20
    elif win_rate >= 50:
        score += 15
    elif win_rate >= 40:
        score += 10
    else:
        score += 5
        if win_rate < 35:
            red_flags.append(f"Win rate {win_rate:.1f}% is too low — needs >40%")

    # Profit factor (25 pts)
    if profit_factor >= 2.0:
        score += 25
    elif profit_factor >= 1.5:
        score += 20
    elif profit_factor >= 1.2:
        score += 15
    else:
        score += 5
        if profit_factor < 1.0:
            red_flags.append("Profit factor < 1.0 — strategy loses money")

    # Drawdown (20 pts)
    if max_drawdown <= 10:
        score += 20
    elif max_drawdown <= 15:
        score += 15
    elif max_drawdown <= 25:
        score += 10
    else:
        score += 5
        if max_drawdown > 30:
            red_flags.append(f"Max DD {max_drawdown:.1f}% — too deep for comfort")

    # Trade count (15 pts)
    trades_per_year = trades / max(years, 1)
    if trades_per_year >= 30:
        score += 15
    elif trades_per_year >= 15:
        score += 10
    elif trades_per_year >= 5:
        score += 5
    else:
        score += 2
        if trades < 30:
            red_flags.append(f"Only {trades} trades — insufficient sample size")

    # CAGR (15 pts)
    if cagr >= 25:
        score += 15
    elif cagr >= 15:
        score += 12
    elif cagr >= 10:
        score += 8
    elif cagr >= 0:
        score += 5
    else:
        score += 0

    # Penalties
    if not slippage_modeled:
        score -= 5
        recommendations.append("Model slippage for realistic results")
    if parameters > 5:
        score -= 10
        red_flags.append(f"{parameters} parameters — risk of overfitting (max 5)")

    # Verdict
    if score >= 75:
        verdict = "DEPLOY"
    elif score >= 50:
        verdict = "REFINE"
    else:
        verdict = "ABANDON"

    # Recommendations
    if win_rate < 50 and profit_factor > 1.5:
        recommendations.append("Let winners run — your avg win is good but needs higher win rate")
    if max_drawdown > 20:
        recommendations.append("Reduce position size to limit drawdown to <15%")
    if cagr < 12:
        recommendations.append("CAGR below NIFTY — reconsider strategy or segment")
    if trades < 50:
        recommendations.append("Run for longer period to get 50+ trades")

    return BacktestResult(
        score=max(0, min(100, score)),
        verdict=verdict,
        profit_factor=round(profit_factor, 2),
        sharpe_ratio=round(sharpe, 2),
        max_drawdown=max_drawdown,
        win_rate=round(win_rate, 1),
        red_flags=red_flags,
        recommendations=recommendations,
    )


def format_backtest_report(result: BacktestResult) -> str:
    """Format backtest evaluation report."""
    lines = []
    lines.append("=" * 60)
    lines.append("🧪 BACKTEST EVALUATION REPORT")
    lines.append("=" * 60)

    if result.verdict == "DEPLOY":
        emoji = "🟢"
    elif result.verdict == "REFINE":
        emoji = "🟡"
    else:
        emoji = "🔴"

    lines.append(f"  Score: {result.score}/100")
    lines.append(f"  Verdict: {emoji} {result.verdict}")
    lines.append(f"\n  METRICS:")
    lines.append(f"    Profit Factor: {result.profit_factor:.2f}")
    lines.append(f"    Sharpe Ratio: {result.sharpe_ratio:.2f}")
    lines.append(f"    Max Drawdown: {result.max_drawdown:.1f}%")
    lines.append(f"    Win Rate: {result.win_rate:.1f}%")

    if result.red_flags:
        lines.append(f"\n  🚩 RED FLAGS:")
        for f in result.red_flags:
            lines.append(f"    • {f}")

    if result.recommendations:
        lines.append(f"\n  💡 RECOMMENDATIONS:")
        for r in result.recommendations:
            lines.append(f"    • {r}")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)
