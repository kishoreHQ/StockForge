"""StockForge Alpha Zoo

Quantitative alpha factors adapted for Indian (NSE/BSE) stocks.
Based on strategies from Kakushadze 101, GTJA 191, Qlib 158, and academic research.

Each alpha factor returns a score where:
- High positive values = bullish signal
- High negative values = bearish signal
- Near zero = neutral

Factors are normalized to 0-100 scale for consistent screening.
"""

import numpy as np
from typing import Dict, List, Optional, Callable


def _rank(series):
    """Cross-sectional rank (percentile)."""
    if len(series) < 2:
        return 0.5
    from scipy.stats import rankdata
    return rankdata(series)[-1] / len(series)


def _ts_mean(arr, window):
    """Time-series mean."""
    arr = np.array(arr)
    if len(arr) < window:
        return float(arr.mean()) if len(arr) > 0 else 0
    return float(arr[-window:].mean())


def _ts_std(arr, window):
    """Time-series standard deviation."""
    arr = np.array(arr)
    if len(arr) < window:
        return float(arr.std()) if len(arr) > 1 else 0
    return float(arr[-window:].std())


def _ts_corr(a, b, window):
    """Rolling correlation between two series."""
    a, b = np.array(a), np.array(b)
    if len(a) < window or len(b) < window:
        return 0
    a_w = a[-window:]
    b_w = b[-window:]
    if np.std(a_w) == 0 or np.std(b_w) == 0:
        return 0
    return float(np.corrcoef(a_w, b_w)[0, 1])


def _ts_sum(arr, window):
    """Time-series sum."""
    arr = np.array(arr)
    if len(arr) < window:
        return float(arr.sum())
    return float(arr[-window:].sum())


def _ts_max(arr, window):
    """Time-series maximum."""
    arr = np.array(arr)
    if len(arr) < window:
        return float(arr.max()) if len(arr) > 0 else 0
    return float(arr[-window:].max())


def _ts_min(arr, window):
    """Time-series minimum."""
    arr = np.array(arr)
    if len(arr) < window:
        return float(arr.min()) if len(arr) > 0 else 0
    return float(arr[-window:].min())


def _delta(arr, period):
    """Difference with period lag."""
    arr = np.array(arr)
    if len(arr) <= period:
        return 0
    return float(arr[-1] - arr[-(period + 1)])


def _signed_power(x, exponent):
    """Signed power: sign(x) * |x|^exponent"""
    return np.sign(x) * (abs(x) ** exponent)


def _normalize(score: float, cap: float = 3.0) -> float:
    """Normalize raw alpha to 0-100 range using tanh capping."""
    capped = max(-cap, min(cap, score)) / cap
    return float((np.tanh(capped * 2) + 1) * 50)


# ──────────────────────────────────────────────
# ALPHA FACTORS
# Each takes price_data dict and returns (score_0_100, detail)
# ──────────────────────────────────────────────


def alpha_momentum_ma10(price_data: dict) -> tuple:
    """MA10 / Close — momentum relative to short MA.
    Original: qlib158 MA10.
    Score > 50 when price above 10-MA.
    """
    close = price_data.get("close", [])
    if len(close) < 11:
        return 50, "Insufficient data"
    ma10 = _ts_mean(close, 10)
    ratio = ma10 / close[-1] if close[-1] > 0 else 1.0
    # ratio > 1 = price below MA (bearish), < 1 = price above MA (bullish)
    raw = (1.0 - ratio) * 10  # ~1% deviation = ±10 points
    return _normalize(raw), f"MA10={ma10:.2f}, Close={close[-1]:.2f}, Ratio={ratio:.4f}"


def alpha_momentum_ma20(price_data: dict) -> tuple:
    """MA20 / Close momentum."""
    close = price_data.get("close", [])
    if len(close) < 21:
        return 50, "Insufficient data"
    ma20 = _ts_mean(close, 20)
    ratio = ma20 / close[-1] if close[-1] > 0 else 1.0
    raw = (1.0 - ratio) * 10
    return _normalize(raw), f"MA20={ma20:.2f}, Close={close[-1]:.2f}, Ratio={ratio:.4f}"


def alpha_volume_trend(price_data: dict) -> tuple:
    """GTJA #32: Correlation of high price rank with volume rank.
    High correlation = strong trend confirmed by volume = bullish.
    """
    high = price_data.get("high", [])
    volume = price_data.get("volume", [])
    if len(high) < 10 or len(volume) < 10:
        return 50, "Insufficient data"
    corr = _ts_corr(high, volume, min(20, len(high)))
    raw = corr * 2  # scale -1:1 to -2:2
    return _normalize(raw), f"High-Volume Corr: {corr:.3f}"


def alpha_reversal_short(price_data: dict) -> tuple:
    """Kakushadze #1: Short-term reversal with volatility adjustment.
    High recent returns + high vol = potential reversal.
    """
    close = price_data.get("close", [])
    if len(close) < 25:
        return 50, "Insufficient data"
    returns = np.diff(np.array(close)) / np.array(close[:-1])
    vol = _ts_std(returns, 20)
    recent_ret = _ts_mean(returns, 5)
    # If recent return is negative and vol is high, expect reversal up
    raw = -recent_ret * (1 + vol * 5)
    return _normalize(raw), f"Returns(5d): {recent_ret:.4f}, Vol: {vol:.4f}"


def alpha_trend_strength(price_data: dict) -> tuple:
    """MA alignment: price > 20MA > 50MA = strong uptrend.
    Inspired by Minervini trend template.
    """
    close = price_data.get("close", [])
    if len(close) < 51:
        return 50, "Insufficient data"
    price = close[-1]
    ma20 = _ts_mean(close, 20)
    ma50 = _ts_mean(close, 50)

    score = 0
    details = []
    if price > ma20 > ma50:
        score += 2
        details.append("Price > 20MA > 50MA")
    elif price > ma20:
        score += 1
        details.append("Price > 20MA")
    elif price < ma20 < ma50:
        score -= 1
        details.append("Price < 20MA < 50MA (downtrend)")
    elif price < ma20:
        score -= 2
        details.append("Price < 20MA")

    # Additional: 50MA > 200MA if available
    if len(close) >= 201:
        ma200 = _ts_mean(close, 200)
        if ma50 > ma200:
            score += 1
            details.append("50MA > 200MA (golden cross)")

    return _normalize(score), "; ".join(details)


def alpha_volatility_regime(price_data: dict) -> tuple:
    """Volatility regime: ATR / Close * 100.
    Low vol = trending (good), High vol = choppy (bad).
    """
    close = price_data.get("close", [])
    high = price_data.get("high", [])
    low = price_data.get("low", [])
    if len(close) < 15 or len(high) < 15 or len(low) < 15:
        return 50, "Insufficient data"

    # ATR approximation
    true_ranges = []
    for i in range(1, min(14, len(close))):
        tr = max(
            high[-i] - low[-i],
            abs(high[-i] - close[-(i + 1)]),
            abs(low[-i] - close[-(i + 1)]),
        )
        true_ranges.append(tr)

    atr = _ts_mean(true_ranges, min(14, len(true_ranges)))
    atr_pct = (atr / close[-1]) * 100 if close[-1] > 0 else 0

    # Nifty stock typical ATR%: 1-3%
    if atr_pct > 5:
        raw = -2  # Extreme vol = bearish
        desc = f"Very high volatility: {atr_pct:.1f}%"
    elif atr_pct > 3:
        raw = -1  # High vol
        desc = f"High volatility: {atr_pct:.1f}%"
    elif atr_pct < 1:
        raw = 1  # Low vol = trending
        desc = f"Low volatility: {atr_pct:.1f}%"
    else:
        raw = 0  # Normal
        desc = f"Normal volatility: {atr_pct:.1f}%"

    return _normalize(raw), desc


def alpha_rsi_reversal(price_data: dict) -> tuple:
    """RSI-style reversal: Oversold bounce or overbought sell."""
    close = price_data.get("close", [])
    if len(close) < 15:
        return 50, "Insufficient data"
    gains, losses = 0, 0
    for i in range(-14, 0):
        chg = close[i] - close[i - 1]
        if chg > 0:
            gains += chg
        else:
            losses += abs(chg)
    avg_gain = gains / 14
    avg_loss = losses / 14
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # RSI < 30 = oversold (buy signal), > 70 = overbought (sell)
    if rsi < 30:
        raw = 2
        desc = f"Oversold: RSI={rsi:.1f}"
    elif rsi < 40:
        raw = 1
        desc = f"Near oversold: RSI={rsi:.1f}"
    elif rsi > 70:
        raw = -2
        desc = f"Overbought: RSI={rsi:.1f}"
    elif rsi > 60:
        raw = -1
        desc = f"Near overbought: RSI={rsi:.1f}"
    else:
        raw = 0
        desc = f"Neutral: RSI={rsi:.1f}"

    return _normalize(raw), desc


def alpha_macd_signal(price_data: dict) -> tuple:
    """MACD crossover: EMA12 vs EMA26."""
    close = price_data.get("close", [])
    if len(close) < 27:
        return 50, "Insufficient data"

    arr = np.array(close)
    ema12 = _ts_mean(arr, 12)
    ema26 = _ts_mean(arr, 26)

    macd = ema12 - ema26
    # Signal line: 9-day MA of MACD
    signal_period = min(9, len(close))
    if len(arr) >= 26 + signal_period:
        # Approximate signal line
        macd_series = []
        for i in range(signal_period):
            slice_arr = arr[-(26 + signal_period - i):]
            if len(slice_arr) >= 26:
                e12 = _ts_mean(slice_arr, 12)
                e26 = _ts_mean(slice_arr, 26)
                macd_series.append(e12 - e26)
        signal_line = _ts_mean(macd_series, signal_period) if macd_series else 0
    else:
        signal_line = 0

    if macd > signal_line:
        raw = 2 if macd > 0 else 1
        desc = f"MACD bullish: {macd:.2f} > signal {signal_line:.2f}"
    elif macd < signal_line:
        raw = -2 if macd < 0 else -1
        desc = f"MACD bearish: {macd:.2f} < signal {signal_line:.2f}"
    else:
        raw = 0
        desc = f"MACD neutral: {macd:.2f}"

    return _normalize(raw), desc


def alpha_bollinger_squeeze(price_data: dict) -> tuple:
    """Bollinger Band Width: indicator of volatility contraction/expansion."""
    close = price_data.get("close", [])
    if len(close) < 21:
        return 50, "Insufficient data"

    price = close[-1]
    ma20 = _ts_mean(close, 20)
    std20 = _ts_std(close, 20)

    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20
    bandwidth = (upper - lower) / ma20 * 100

    # Position within bands
    if std20 == 0:
        pos = 0.5
    else:
        pos = (price - lower) / (upper - lower)

    # Narrow bands (squeeze) = big move coming
    if bandwidth < 5:
        raw = 1 if pos > 0.5 else -1
        desc = f"BB squeeze ({bandwidth:.1f}% width) — breakout imminent"
    elif bandwidth > 20:
        raw = -0.5
        desc = f"BB wide ({bandwidth:.1f}% width) — potential reversal"
    elif pos > 0.8:
        raw = -1
        desc = f"Near upper BB (pos {pos:.0%}) — overextended"
    elif pos < 0.2:
        raw = 1
        desc = f"Near lower BB (pos {pos:.0%}) — potential bounce"
    else:
        raw = 0
        desc = f"BB neutral: width {bandwidth:.1f}%, position {pos:.0%}"

    return _normalize(raw), desc


def alpha_price_volume_divergence(price_data: dict) -> tuple:
    """Price-volume divergence: Price up but volume down = weak rally."""
    close = price_data.get("close", [])
    volume = price_data.get("volume", [])
    if len(close) < 11 or len(volume) < 11:
        return 50, "Insufficient data"

    price_chg = _delta(close, 5) / close[-6] if len(close) > 6 else 0
    vol_avg = _ts_mean(volume, 10)
    vol_recent = _ts_mean(volume, 3)

    vol_ratio = vol_recent / vol_avg if vol_avg > 0 else 1.0

    if price_chg > 0.02 and vol_ratio > 1.3:
        raw = 2
        desc = f"Strong: +{price_chg*100:.1f}% on {vol_ratio:.1f}x volume"
    elif price_chg > 0.02 and vol_ratio < 0.8:
        raw = -1
        desc = f"Weak rally: +{price_chg*100:.1f}% but low vol ({vol_ratio:.1f}x)"
    elif price_chg < -0.02 and vol_ratio > 1.3:
        raw = -2
        desc = f"Distribution: -{abs(price_chg)*100:.1f}% on {vol_ratio:.1f}x volume"
    elif price_chg < -0.02 and vol_ratio < 0.8:
        raw = 0.5
        desc = f"Mild decline: -{abs(price_chg)*100:.1f}% on low vol ({vol_ratio:.1f}x)"
    else:
        raw = 0
        desc = f"Normal: {price_chg*100:+.2f}% on {vol_ratio:.1f}x volume"

    return _normalize(raw), desc


# Registry
ALPHA_FACTORS: Dict[str, Dict] = {
    "momentum_ma10": {
        "name": "MA10 Momentum",
        "func": alpha_momentum_ma10,
        "theme": "momentum",
        "horizon": "short (10d)",
        "description": "Price vs 10-day MA ratio",
    },
    "momentum_ma20": {
        "name": "MA20 Momentum",
        "func": alpha_momentum_ma20,
        "theme": "momentum",
        "horizon": "medium (20d)",
        "description": "Price vs 20-day MA ratio",
    },
    "volume_trend": {
        "name": "Volume Trend Correlation",
        "func": alpha_volume_trend,
        "theme": "volume",
        "horizon": "medium (20d)",
        "description": "High/Volume rank correlation (GTJA #32)",
    },
    "reversal_short": {
        "name": "Short-term Reversal",
        "func": alpha_reversal_short,
        "theme": "reversal",
        "horizon": "short (5d)",
        "description": "Kakushadze #1 volatility-adjusted reversal",
    },
    "trend_strength": {
        "name": "Trend Strength",
        "func": alpha_trend_strength,
        "theme": "trend",
        "horizon": "long (50d)",
        "description": "MA alignment (Minervini trend template)",
    },
    "volatility_regime": {
        "name": "Volatility Regime",
        "func": alpha_volatility_regime,
        "theme": "volatility",
        "horizon": "medium (14d)",
        "description": "ATR% based volatility classification",
    },
    "rsi_reversal": {
        "name": "RSI Reversal",
        "func": alpha_rsi_reversal,
        "theme": "reversal",
        "horizon": "medium (14d)",
        "description": "RSI oversold/overbought signals",
    },
    "macd_signal": {
        "name": "MACD Signal",
        "func": alpha_macd_signal,
        "theme": "momentum",
        "horizon": "medium (26d)",
        "description": "MACD line vs signal line crossover",
    },
    "bollinger_squeeze": {
        "name": "Bollinger Squeeze",
        "func": alpha_bollinger_squeeze,
        "theme": "volatility",
        "horizon": "medium (20d)",
        "description": "BB width contraction/expansion signals",
    },
    "price_volume_divergence": {
        "name": "Price-Volume Divergence",
        "func": alpha_price_volume_divergence,
        "theme": "volume",
        "horizon": "short (5d)",
        "description": "Volume confirmation of price moves",
    },
}


def score_all_alphas(price_data: dict) -> Dict:
    """Run all alpha factors on a stock's price data."""
    results = {}
    total_score = 0
    active_count = 0

    for key, alpha in ALPHA_FACTORS.items():
        try:
            score, detail = alpha["func"](price_data)
            results[key] = {
                "score": round(score, 1),
                "signal": _signal_label(score),
                "detail": detail,
                "theme": alpha["theme"],
            }
            total_score += (score - 50) / 50  # normalize contribution
            active_count += 1
        except Exception as e:
            results[key] = {"score": 50, "signal": "neutral", "detail": f"Error: {str(e)}"}

    # Aggregate score (0-100)
    agg = 50 + (total_score / max(active_count, 1)) * 25 if active_count > 0 else 50
    agg = max(0, min(100, agg))

    # Theme aggregation
    themes = {}
    for key, r in results.items():
        t = r.get("theme", "other")
        if t not in themes:
            themes[t] = []
        themes[t].append(r["score"])

    theme_scores = {}
    for t, scores in themes.items():
        theme_scores[t] = round(sum(scores) / len(scores), 1)

    return {
        "aggregate": round(agg, 1),
        "signal": _signal_label(agg),
        "factors": results,
        "themes": theme_scores,
        "active_factors": active_count,
    }


def _signal_label(score: float) -> str:
    if score >= 75:
        return "strong_buy"
    elif score >= 60:
        return "buy"
    elif score >= 40:
        return "neutral"
    elif score >= 25:
        return "sell"
    return "strong_sell"


def top_stocks_by_alpha(stocks_data: Dict[str, dict], top_n: int = 10) -> list:
    """Score multiple stocks and return top-ranked by aggregate alpha signal."""
    scored = []
    for symbol, price_data in stocks_data.items():
        try:
            result = score_all_alphas(price_data)
            scored.append({
                "symbol": symbol,
                "alpha_score": result["aggregate"],
                "signal": result["signal"],
                "themes": result["themes"],
            })
        except Exception:
            continue

    scored.sort(key=lambda x: x["alpha_score"], reverse=True)
    return scored[:top_n]
