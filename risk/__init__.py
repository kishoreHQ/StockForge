"""
StockForge Risk Management Suite
Position sizing, stop-loss strategies, trailing stops, and risk-reward analysis.
Adapted from Bhala-Srinivash/nse-trading-skills + Mark Minervini principles.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionSize:
    shares: int
    capital_at_risk: float
    entry_price: float
    stop_loss: float
    risk_per_share: float
    portfolio_pct: float
    method: str
    r_multiple: float = 0.0
    expected_value: float = 0.0


@dataclass
class StopLossPlan:
    stop_price: float
    method: str
    buffer_pct: float
    distance_pct: float
    rationale: str


@dataclass
class TrailingStopPlan:
    method: str
    initial_stop: float
    trail_rules: list
    current_trail: float


def position_size_fixed_fractional(
    account_size: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
    max_portfolio_pct: float = 25.0,
) -> PositionSize:
    """Fixed fractional: risk X% of account on the trade."""
    capital_at_risk = account_size * (risk_pct / 100.0)
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share <= 0:
        return PositionSize(0, 0, entry_price, stop_loss, 0, 0, "fixed_fractional")
    shares = int(capital_at_risk / risk_per_share)
    position_value = shares * entry_price
    portfolio_pct = (position_value / account_size) * 100.0
    # Cap at max portfolio allocation
    if portfolio_pct > max_portfolio_pct:
        max_shares = int((account_size * max_portfolio_pct / 100.0) / entry_price)
        shares = min(shares, max_shares)
        position_value = shares * entry_price
        portfolio_pct = (position_value / account_size) * 100.0
    return PositionSize(
        shares=shares,
        capital_at_risk=capital_at_risk,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_per_share=risk_per_share,
        portfolio_pct=portfolio_pct,
        method="Fixed Fractional",
    )


def position_size_atr_based(
    account_size: float,
    risk_pct: float,
    entry_price: float,
    atr: float,
    atr_multiplier: float = 2.0,
    max_portfolio_pct: float = 25.0,
) -> PositionSize:
    """ATR-based: stop = entry - (ATR * multiplier)."""
    stop_loss = entry_price - (atr * atr_multiplier)
    return position_size_fixed_fractional(
        account_size, risk_pct, entry_price, stop_loss, max_portfolio_pct
    )


def position_size_kelly_criterion(
    account_size: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    entry_price: float,
    stop_loss: float,
    max_kelly_pct: float = 25.0,
    max_portfolio_pct: float = 25.0,
) -> PositionSize:
    """Kelly Criterion: f* = (bp - q) / b where b=win/loss ratio, p=win_rate, q=1-p."""
    b = avg_win / avg_loss if avg_loss > 0 else 1
    p = win_rate / 100.0
    q = 1.0 - p
    kelly_fraction = (b * p - q) / b
    kelly_fraction = max(0, min(kelly_fraction, max_kelly_pct / 100.0))
    capital_at_risk = account_size * kelly_fraction
    risk_per_share = abs(entry_price - stop_loss)
    shares = int(capital_at_risk / risk_per_share) if risk_per_share > 0 else 0
    position_value = shares * entry_price
    portfolio_pct = (position_value / account_size) * 100.0
    if portfolio_pct > max_portfolio_pct:
        max_shares = int((account_size * max_portfolio_pct / 100.0) / entry_price)
        shares = min(shares, max_shares)
        position_value = shares * entry_price
        portfolio_pct = (position_value / account_size) * 100.0
    return PositionSize(
        shares=shares,
        capital_at_risk=capital_at_risk,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_per_share=risk_per_share,
        portfolio_pct=portfolio_pct,
        method="Kelly Criterion",
    )


def calculate_stop_loss(
    entry_price: float,
    method: str = "structure",
    support_level: Optional[float] = None,
    atr: Optional[float] = None,
    atr_multiplier: float = 2.0,
    moving_avg: Optional[float] = None,
    buffer_pct: float = 1.0,
) -> StopLossPlan:
    """Calculate stop-loss using different methods with buffer."""
    if method == "structure" and support_level:
        stop = support_level * (1 - buffer_pct / 100.0)
        rationale = f"Below support at ₹{support_level:.2f} with {buffer_pct}% buffer"
    elif method == "atr" and atr:
        stop = entry_price - (atr * atr_multiplier)
        rationale = f"{atr_multiplier}x ATR (₹{atr:.2f}) below entry"
    elif method == "moving_avg" and moving_avg:
        stop = moving_avg * (1 - buffer_pct / 100.0)
        rationale = f"Below MA with {buffer_pct}% buffer"
    else:
        # Default: 5% below entry for swing, 8% for investing
        stop = entry_price * 0.95
        rationale = "Default: 5% below entry (swing trading)"

    distance = ((entry_price - stop) / entry_price) * 100.0
    return StopLossPlan(
        stop_price=round(stop, 2),
        method=method,
        buffer_pct=buffer_pct,
        distance_pct=round(distance, 2),
        rationale=rationale,
    )


def calculate_trailing_stop(
    entry_price: float,
    current_price: float,
    atr: Optional[float] = None,
    method: str = "atr",
    atr_multiplier: float = 2.0,
    highest_since_entry: Optional[float] = None,
) -> TrailingStopPlan:
    """Calculate trailing stop that moves up as price rises."""
    peak = highest_since_entry or current_price
    rules = []
    if method == "atr" and atr:
        trail = peak - (atr * atr_multiplier)
        rules.append(f"Trail at {atr_multiplier}x ATR below peak (₹{peak:.2f})")
    elif method == "percentage":
        trail = peak * 0.92  # 8% trail
        rules.append("Trail 8% below highest price")
    elif method == "chandelier":
        if atr:
            trail = peak - (atr * 3.0)
            rules.append("Chandelier Exit: 3x ATR below 22-day high")
        else:
            trail = peak * 0.90
            rules.append("Fallback: 10% below peak")
    else:
        trail = peak * 0.93
        rules.append("Default: 7% below peak")

    # Never trail below entry (for long positions)
    if trail < entry_price:
        trail = entry_price
        rules.append("Stop locked at entry (no loss)")

    return TrailingStopPlan(
        method=method,
        initial_stop=entry_price * 0.95,
        trail_rules=rules,
        current_trail=round(trail, 2),
    )


def calculate_risk_reward(
    entry: float, stop_loss: float, target: float, win_rate: Optional[float] = None
) -> dict:
    """Calculate R:R ratio and expected value."""
    risk = entry - stop_loss
    reward = target - entry
    if risk <= 0:
        return {"error": "Stop loss must be below entry for long positions"}
    rr = reward / risk
    # Minimum R:R by win rate
    if win_rate:
        p = win_rate / 100.0
        min_rr = (1 - p) / p if p < 1 else 0
    else:
        min_rr = 2.0  # Default: need 1:2 R:R

    expected_value = 0
    if win_rate:
        p = win_rate / 100.0
        expected_value = (p * reward) - ((1 - p) * risk)

    verdict = "GOOD" if rr >= max(min_rr, 2.0) else "MARGINAL" if rr >= 1.5 else "POOR"

    return {
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "rr_ratio": round(rr, 2),
        "min_rr_required": round(min_rr, 2),
        "expected_value": round(expected_value, 2),
        "verdict": verdict,
    }


def generate_risk_report(
    account_size: float,
    entry_price: float,
    stop_loss_price: float,
    target_price: float,
    atr: Optional[float] = None,
    atr_multiplier: float = 2.0,
    support_level: Optional[float] = None,
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None,
    risk_pct: float = 2.0,
) -> str:
    """Generate comprehensive risk management report."""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 STOCKFORGE RISK MANAGEMENT REPORT")
    lines.append("=" * 60)

    # Position sizing (3 methods)
    lines.append(f"\n📏 POSITION SIZING (Account: ₹{account_size:,.0f}, Risk: {risk_pct}%)")
    lines.append("-" * 50)

    ff = position_size_fixed_fractional(account_size, risk_pct, entry_price, stop_loss_price)
    lines.append(f"  Fixed Fractional: {ff.shares} shares (₹{ff.portfolio_pct:.1f}% of portfolio)")
    lines.append(f"    Capital at risk: ₹{ff.capital_at_risk:,.0f}")

    if atr:
        atr_ps = position_size_atr_based(account_size, risk_pct, entry_price, atr, atr_multiplier)
        lines.append(f"  ATR-Based ({atr_multiplier}x): {atr_ps.shares} shares (₹{atr_ps.portfolio_pct:.1f}%)")
        lines.append(f"    Stop at: ₹{atr_ps.stop_loss:.2f}")

    if win_rate and avg_win and avg_loss:
        kelly = position_size_kelly_criterion(
            account_size, win_rate, avg_win, avg_loss, entry_price, stop_loss_price
        )
        lines.append(f"  Kelly Criterion: {kelly.shares} shares (₹{kelly.portfolio_pct:.1f}%)")

    # Stop-loss analysis
    lines.append(f"\n🛑 STOP-LOSS ANALYSIS")
    lines.append("-" * 50)
    sl = calculate_stop_loss(entry_price, "structure", support_level, atr, atr_multiplier)
    lines.append(f"  Method: {sl.method}")
    lines.append(f"  Stop Price: ₹{sl.stop_price:.2f}")
    lines.append(f"  Distance from entry: {sl.distance_pct:.2f}%")
    lines.append(f"  Rationale: {sl.rationale}")

    # Trailing stop
    if atr:
        trail = calculate_trailing_stop(entry_price, entry_price, atr, "atr", atr_multiplier)
        lines.append(f"\n📈 TRAILING STOP PLAN")
        lines.append("-" * 50)
        lines.append(f"  Method: {trail.method}")
        lines.append(f"  Rules: {'; '.join(trail.trail_rules)}")

    # Risk-Reward
    lines.append(f"\n⚖️ RISK-REWARD ANALYSIS")
    lines.append("-" * 50)
    rr = calculate_risk_reward(entry_price, stop_loss_price, target_price, win_rate)
    lines.append(f"  Entry: ₹{entry_price:.2f}")
    lines.append(f"  Stop: ₹{stop_loss_price:.2f}")
    lines.append(f"  Target: ₹{target_price:.2f}")
    lines.append(f"  Risk per share: ₹{rr['risk']:.2f}")
    lines.append(f"  Reward per share: ₹{rr['reward']:.2f}")
    lines.append(f"  R:R Ratio: 1:{rr['rr_ratio']:.2f}")
    lines.append(f"  Verdict: {rr['verdict']}")
    if 'expected_value' in rr:
        lines.append(f"  Expected Value: ₹{rr['expected_value']:.2f}")

    # Cost considerations (Indian market)
    brokerage = entry_price * 0.0003  # ~0.03% discount broker
    stt = entry_price * 0.001  # 0.1% STT on delivery
    total_costs = (brokerage + stt) * 2  # buy + sell
    lines.append(f"\n💰 COST ESTIMATE (per share)")
    lines.append("-" * 50)
    lines.append(f"  Brokerage + STT + GST: ~₹{total_costs:.2f}")
    lines.append(f"  Net R:R after costs: 1:{max(0, rr['rr_ratio'] - (total_costs / rr['risk'])):.2f}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
