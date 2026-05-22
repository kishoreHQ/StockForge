"""StockForge Confidence Scorer

Calculate confidence scores (0.0 to 1.0) for trading signals based on:
- Technical indicator alignment across multiple timeframes
- Trend strength (MA alignment)
- Volume confirmation
- Risk/reward ratio quality
- Market volatility (VIX-adjusted)
- Fundamental score integration
- Sector/peer relative strength

Adapted from FinceptTerminal's ConfidenceScorer with Indian market extensions.
"""

from typing import Dict, List, Optional
import math


class StockForgeConfidenceScorer:
    """Calculate confidence scores (0.0 to 1.0) for Indian stock trading signals."""

    # Default weights tuned for Indian market conditions
    DEFAULT_WEIGHTS = {
        'indicators': 0.25,
        'trend': 0.20,
        'volume': 0.15,
        'risk_reward': 0.15,
        'volatility': 0.10,
        'fundamental': 0.10,
        'sector_momentum': 0.05,
    }

    @staticmethod
    def comprehensive_score(
        indicator_alignment: float = 0.5,
        trend_strength: float = 0.5,
        volume_confirmation: float = 0.5,
        risk_reward_ratio: float = 2.0,
        volatility_factor: float = 0.5,
        fundamental_score: Optional[float] = None,
        sector_momentum: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """Calculate overall confidence score with full breakdown.

        Args:
            indicator_alignment: 0-1, how many indicators agree
            trend_strength: 0-1, strength of trend (MA alignment)
            volume_confirmation: 0-1, volume supports the move
            risk_reward_ratio: Actual R:R ratio (e.g. 2.5 for 1:2.5)
            volatility_factor: 0-1, volatility level (0=low, 1=high)
            fundamental_score: 0-100, from StockForge fundamental scoring
            sector_momentum: -1 to 1, sector relative strength
            weights: Custom weights for each factor

        Returns:
            Dict with confidence, breakdown, rating, and action recommendation
        """
        if weights is None:
            weights = StockForgeConfidenceScorer.DEFAULT_WEIGHTS.copy()

        # Normalize risk/reward to 0-1 (2.5:1 = 0.83, 3:1 = 1.0)
        rr_normalized = min(risk_reward_ratio / 3.0, 1.0)

        # Lower volatility = higher confidence
        volatility_score = 1.0 - volatility_factor

        # Normalize fundamental score (0-100 → 0-1)
        fund_normalized = fundamental_score / 100.0 if fundamental_score is not None else 0.5

        # Normalize sector momentum (-1 to 1 → 0 to 1)
        sector_norm = (sector_momentum + 1.0) / 2.0 if sector_momentum is not None else 0.5

        # Calculate weighted score
        confidence = (
            indicator_alignment * weights['indicators'] +
            trend_strength * weights['trend'] +
            volume_confirmation * weights['volume'] +
            rr_normalized * weights['risk_reward'] +
            volatility_score * weights['volatility'] +
            fund_normalized * weights.get('fundamental', 0) +
            sector_norm * weights.get('sector_momentum', 0)
        )

        # Ensure 0-1 range
        confidence = max(0.0, min(1.0, confidence))

        return {
            "confidence": round(confidence, 3),
            "rating": StockForgeConfidenceScorer._rating(confidence),
            "action": StockForgeConfidenceScorer._action(confidence),
            "breakdown": {
                "indicator_alignment": round(indicator_alignment, 2),
                "trend_strength": round(trend_strength, 2),
                "volume_confirmation": round(volume_confirmation, 2),
                "risk_reward_score": round(rr_normalized, 2),
                "volatility_score": round(volatility_score, 2),
                "fundamental_score": round(fund_normalized, 2) if fundamental_score is not None else None,
                "sector_momentum": round(sector_norm, 2) if sector_momentum is not None else None,
            },
        }

    @staticmethod
    def from_technical_indicators(
        indicators: Dict[str, str],
        current_price: float,
        ma_20: float,
        ma_50: float,
        ma_200: Optional[float] = None,
        current_volume: Optional[float] = None,
        avg_volume: Optional[float] = None,
        vix: Optional[float] = None,
        risk_reward: float = 2.0,
        fundamental_score: Optional[float] = None,
        sector_momentum: Optional[float] = None,
    ) -> Dict:
        """Calculate confidence directly from market data.

        Args:
            indicators: Dict of indicator signals, e.g.
                {'RSI': 'buy', 'MACD': 'buy', 'EMA': 'sell', 'BB': 'buy', 'Stoch': 'neutral'}
            current_price: Current market price
            ma_20: 20-period MA
            ma_50: 50-period MA
            ma_200: 200-period MA (optional)
            current_volume: Current volume
            avg_volume: Average volume
            vix: India VIX value
            risk_reward: Risk/reward ratio
            fundamental_score: 0-100 fundamental score
            sector_momentum: -1 to 1 sector momentum
        """
        indicator_alignment = StockForgeConfidenceScorer._calc_indicator_alignment(indicators)
        trend_strength = StockForgeConfidenceScorer._calc_trend_strength(
            current_price, ma_20, ma_50, ma_200
        )
        volume_confirmation = StockForgeConfidenceScorer._calc_volume_confirmation(
            current_volume, avg_volume
        ) if current_volume is not None and avg_volume is not None else 0.5
        volatility_factor = StockForgeConfidenceScorer._calc_volatility_factor(vix) if vix else 0.5

        return StockForgeConfidenceScorer.comprehensive_score(
            indicator_alignment=indicator_alignment,
            trend_strength=trend_strength,
            volume_confirmation=volume_confirmation,
            risk_reward_ratio=risk_reward,
            volatility_factor=volatility_factor,
            fundamental_score=fundamental_score,
            sector_momentum=sector_momentum,
        )

    @staticmethod
    def _calc_indicator_alignment(indicators: Dict[str, str]) -> float:
        """How well indicators align on same direction."""
        if not indicators:
            return 0.5
        signals = list(indicators.values())
        buy_count = signals.count('buy') + signals.count('bullish')
        sell_count = signals.count('sell') + signals.count('bearish')
        total = len(signals)
        alignment = max(buy_count, sell_count) / total if total > 0 else 0
        return alignment

    @staticmethod
    def _calc_trend_strength(
        price: float, ma_20: float, ma_50: float, ma_200: Optional[float] = None
    ) -> float:
        """Trend strength from MA alignment."""
        score = 0.0
        if price > ma_20 > ma_50:
            score = 0.6
        elif price < ma_20 < ma_50:
            score = 0.6
        if ma_200:
            if (price > ma_20 > ma_50 > ma_200) or (price < ma_20 < ma_50 < ma_200):
                score = 1.0
        return score

    @staticmethod
    def _calc_volume_confirmation(current: float, avg: float, threshold: float = 1.2) -> float:
        """Volume confirmation score."""
        if avg == 0:
            return 0.5
        ratio = current / avg
        if ratio >= threshold:
            return min(ratio / 2.0, 1.0)
        return 0.3

    @staticmethod
    def _calc_volatility_factor(vix: float) -> float:
        """Convert VIX to 0-1 volatility factor."""
        # India VIX: <15 = low, 15-25 = normal, 25-35 = high, >35 = extreme
        if vix <= 15:
            return 0.1
        elif vix <= 25:
            return 0.3
        elif vix <= 35:
            return 0.6
        else:
            return min(1.0, (vix - 25) / 40)

    @staticmethod
    def _rating(confidence: float) -> str:
        if confidence >= 0.8:
            return "Very High"
        elif confidence >= 0.7:
            return "High"
        elif confidence >= 0.6:
            return "Medium"
        elif confidence >= 0.5:
            return "Low"
        return "Very Low"

    @staticmethod
    def _action(confidence: float, min_threshold: float = 0.6) -> str:
        if confidence >= 0.8:
            return "STRONG_EXECUTE"
        elif confidence >= 0.7:
            return "EXECUTE"
        elif confidence >= 0.6:
            return "EXECUTE_WITH_CAUTION"
        return "SKIP"

    @staticmethod
    def score_from_stockforge_rec(rec: dict) -> Dict:
        """Score confidence directly from a StockForge recommendation dict."""
        tech = rec.get("technical", {})
        quote = rec.get("quote", {})
        fundamental = rec.get("fundamental", {})

        # Build indicator signals from StockForge's analysis
        indicators = {}
        signals = tech.get("signals", [])
        for s in signals:
            if "✅" in s or "BULL" in s.upper():
                indicators["trend"] = "bullish"
            elif "⚠️" in s or "BEAR" in s.upper():
                indicators["trend"] = "bearish"

        # Make use of various technical signals
        indicators["rsi"] = _signal_from_range(tech.get("rsi", 50), 30, 70)
        if "macd_signal" in tech:
            indicators["macd"] = "buy" if tech["macd_signal"] == "bullish" else "sell"

        price = quote.get("price", 0)
        ma_20 = tech.get("sma_20", price)
        ma_50 = tech.get("sma_50", price)
        fundamental_score = fundamental.get("score", None)

        return StockForgeConfidenceScorer.from_technical_indicators(
            indicators=indicators,
            current_price=price,
            ma_20=ma_20,
            ma_50=ma_50,
            fundamental_score=fundamental_score,
        )


def _signal_from_range(value, lower, upper):
    """Convert numerical value to buy/sell/neutral signal."""
    if value <= lower:
        return "buy"
    elif value >= upper:
        return "sell"
    return "neutral"
