"""StockForge Dynamic TP/SL Calculator

Calculate adaptive take-profit and stop-loss levels based on:
- Current volatility (ATR) for Indian stocks
- Support/resistance levels from recent price action
- Market regime (trending/ranging/volatile)
- Risk/reward targets tuned to NSE market behavior

Integrated with existing StockForge risk management system.
"""

from typing import Dict, Optional, Tuple
import math


class DynamicTPSL:
    """Dynamic Take Profit and Stop Loss for Indian stocks."""

    @staticmethod
    def from_atr(
        entry_price: float,
        direction: str,
        atr: float,
        risk_reward_ratio: float = 2.0,
        atr_multiplier: float = 2.0,
        premium_stock: bool = False,
    ) -> Dict:
        """Calculate TP/SL based on ATR volatility.

        For Indian markets:
        - Premium stocks (₹1000+): tighter SL (1.5x ATR)
        - Mid-range (₹100-1000): standard 2x ATR
        - Penny stocks (<₹100): wider SL (2.5x ATR)
        """
        # Adjust ATR multiplier based on price range
        if premium_stock:
            adjusted_mult = atr_multiplier * 0.75
        elif entry_price < 100:
            adjusted_mult = atr_multiplier * 1.25
        else:
            adjusted_mult = atr_multiplier

        sl_distance = atr * adjusted_mult

        if direction.lower() == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * risk_reward_ratio)
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * risk_reward_ratio)

        # Ensure stop loss isn't below 0
        if direction.lower() == 'long' and stop_loss <= 0:
            stop_loss = entry_price * 0.85  # 15% as absolute floor

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "sl_distance": round(sl_distance, 2),
            "tp_distance": round(sl_distance * risk_reward_ratio, 2),
            "risk_reward_ratio": risk_reward_ratio,
            "method": f"ATR ({atr_multiplier:.1f}x)",
        }

    @staticmethod
    def from_support_resistance(
        entry: float,
        direction: str,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        atr: Optional[float] = None,
        buffer_pct: float = 1.0,
    ) -> Dict:
        """Calculate TP/SL using support/resistance levels with ATR buffer.

        Primary: use structural S/R levels
        Fallback: use ATR-based levels if S/R unavailable
        """
        if direction.lower() == 'long' and support:
            sl_distance = abs(entry - support)
            buffer = sl_distance * (buffer_pct / 100.0)
            stop_loss = support - buffer
            take_profit = resistance if resistance else entry + (sl_distance * 2)
            method = "Support/Resistance"
        elif direction.lower() == 'short' and resistance:
            sl_distance = abs(resistance - entry)
            buffer = sl_distance * (buffer_pct / 100.0)
            stop_loss = resistance + buffer
            take_profit = support if support else entry - (sl_distance * 2)
            method = "Support/Resistance"
        elif atr:
            # Fallback to ATR
            return DynamicTPSL.from_atr(entry, direction, atr)
        else:
            # Fallback to percentage
            return DynamicTPSL.from_percentage(entry, direction)

        if direction.lower() == 'long' and stop_loss <= 0:
            stop_loss = entry * 0.85

        reward = abs(take_profit - entry)
        risk = abs(entry - stop_loss)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward_ratio": rr,
            "method": method,
        }

    @staticmethod
    def from_percentage(
        entry_price: float,
        direction: str,
        sl_percent: float = 2.0,
        tp_percent: float = 5.0,
    ) -> Dict:
        """Simple percentage-based TP/SL."""
        sl_amount = entry_price * (sl_percent / 100)
        tp_amount = entry_price * (tp_percent / 100)

        if direction.lower() == 'long':
            stop_loss = entry_price - sl_amount
            take_profit = entry_price + tp_amount
        else:
            stop_loss = entry_price + sl_amount
            take_profit = entry_price - tp_amount

        if direction.lower() == 'long' and stop_loss <= 0:
            stop_loss = entry_price * 0.85

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "sl_percent": sl_percent,
            "tp_percent": tp_percent,
            "risk_reward_ratio": round(tp_percent / sl_percent, 2),
            "method": f"Percentage ({sl_percent}%/{tp_percent}%)",
        }

    @staticmethod
    def trailing(
        entry_price: float,
        current_price: float,
        direction: str,
        trail_percent: float = 1.0,
        atr: Optional[float] = None,
        atr_multiplier: float = 2.0,
    ) -> float:
        """Calculate trailing stop that only moves in favorable direction."""
        if direction.lower() == 'long':
            if atr:
                trailing = current_price - (atr * atr_multiplier)
            else:
                trailing = current_price * (1 - trail_percent / 100)
            original = entry_price * (1 - trail_percent / 100)
            return max(trailing, original)
        else:
            if atr:
                trailing = current_price + (atr * atr_multiplier)
            else:
                trailing = current_price * (1 + trail_percent / 100)
            original = entry_price * (1 + trail_percent / 100)
            return min(trailing, original)

    @staticmethod
    def estimate_volatility(prices: list, period: int = 14) -> float:
        """Estimate volatility from price history (ATR approximation)."""
        if len(prices) < period + 1:
            return prices[-1] * 0.02 if prices else 0
        ranges = []
        for i in range(len(prices) - period, len(prices)):
            if i > 0:
                ranges.append(abs(prices[i] - prices[i - 1]))
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        return avg_range

    @staticmethod
    def validate(
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        min_risk_reward: float = 1.5,
    ) -> Dict:
        """Validate TP/SL levels and flag issues."""
        errors = []
        warnings = []

        if direction.lower() == 'long':
            if stop_loss >= entry_price:
                errors.append("Stop loss must be below entry price for long positions")
            if take_profit <= entry_price:
                errors.append("Take profit must be above entry price for long positions")
            if stop_loss < entry_price and take_profit > entry_price:
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
                rr = reward / risk if risk > 0 else 0
                if rr < min_risk_reward:
                    warnings.append(f"R:R ratio {rr:.2f} below minimum {min_risk_reward}")
        else:
            if stop_loss <= entry_price:
                errors.append("Stop loss must be above entry price for short positions")
            if take_profit >= entry_price:
                errors.append("Take profit must be below entry price for short positions")
            if stop_loss > entry_price and take_profit < entry_price:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
                rr = reward / risk if risk > 0 else 0
                if rr < min_risk_reward:
                    warnings.append(f"R:R ratio {rr:.2f} below minimum {min_risk_reward}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def generate_report(
        entry: float,
        direction: str = "long",
        atr: Optional[float] = None,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        prices: Optional[list] = None,
    ) -> str:
        """Generate a complete TP/SL report string for display."""
        lines = []
        lines.append("📐 DYNAMIC TP/SL CALCULATION")
        lines.append("-" * 40)

        if atr is None and prices:
            atr = DynamicTPSL.estimate_volatility(prices)

        # Generate all methods
        methods = {}

        if atr:
            for rr in [1.5, 2.0, 3.0]:
                methods[f"ATR {rr}:1"] = DynamicTPSL.from_atr(entry, direction, atr, rr)

        if support or resistance:
            s_r = DynamicTPSL.from_support_resistance(entry, direction, support, resistance, atr)
            methods["S/R Based"] = s_r

        # Always add percentage
        methods["5%/10%"] = DynamicTPSL.from_percentage(entry, direction, 5, 10)

        for name, result in methods.items():
            lines.append(f"\n  {name}:")
            lines.append(f"    SL: ₹{result['stop_loss']:.2f}")
            lines.append(f"    TP: ₹{result['take_profit']:.2f}")
            lines.append(f"    R:R: 1:{result.get('risk_reward_ratio', 0):.2f}")

        # Also add trailing stop example
        lines.append(f"\n  📈 Trailing Stop:")
        trail = DynamicTPSL.trailing(entry, entry, direction, 2.0, atr, 2.0)
        lines.append(f"    Initial trail: ₹{trail:.2f}")
        if atr:
            trail2 = DynamicTPSL.trailing(entry, entry * 1.1, direction, 2.0, atr, 2.0)
            lines.append(f"    After 10% up: ₹{trail2:.2f}")

        return "\n".join(lines)
