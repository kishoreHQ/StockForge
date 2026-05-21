"""StockForge Analysis - Technical indicators."""
import pandas as pd
import numpy as np
from data.market_data import get_history, get_quote, nse_symbol


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD line, signal line, and histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line.iloc[-1], 3),
        "signal": round(signal_line.iloc[-1], 3),
        "histogram": round(histogram.iloc[-1], 3),
        "trend": "bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "bearish",
    }


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """Calculate Bollinger Bands."""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    current = prices.iloc[-1]
    bandwidth = ((upper.iloc[-1] - lower.iloc[-1]) / sma.iloc[-1]) * 100
    
    # Position within bands
    if upper.iloc[-1] != lower.iloc[-1]:
        position = ((current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])) * 100
    else:
        position = 50
    
    return {
        "upper": round(upper.iloc[-1], 2),
        "middle": round(sma.iloc[-1], 2),
        "lower": round(lower.iloc[-1], 2),
        "current": round(current, 2),
        "position_pct": round(position, 1),
        "bandwidth_pct": round(bandwidth, 2),
        "signal": (
            "Overbought (near upper band)" if position > 80
            else "Oversold (near lower band)" if position < 20
            else "Within bands"
        ),
    }


def calculate_sma_ema(prices: pd.Series) -> dict:
    """Calculate key moving averages."""
    result = {}
    periods = [20, 50, 100, 200]
    
    for p in periods:
        if len(prices) >= p:
            sma = prices.rolling(window=p).mean().iloc[-1]
            ema = prices.ewm(span=p, adjust=False).mean().iloc[-1]
            result[f"sma_{p}"] = round(sma, 2)
            result[f"ema_{p}"] = round(ema, 2)
    
    current = prices.iloc[-1]
    
    # Price vs MAs
    result["price"] = round(current, 2)
    result["above_sma_20"] = current > result.get("sma_20", 0)
    result["above_sma_50"] = current > result.get("sma_50", 0)
    result["above_sma_200"] = current > result.get("sma_200", 0)
    
    # Golden/Death cross
    if "sma_50" in result and "sma_200" in result:
        result["golden_cross"] = result["sma_50"] > result["sma_200"]
    
    return result


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return round(tr.rolling(window=period).mean().iloc[-1], 2)


def find_support_resistance(prices: pd.Series, high: pd.Series, low: pd.Series) -> dict:
    """Identify support and resistance levels using pivot points."""
    recent = prices.tail(60)
    highs = high.tail(60)
    lows = low.tail(60)
    
    # Simple pivot: local maxima/minima
    resistance = []
    support = []
    
    for i in range(2, len(recent) - 2):
        if recent.iloc[i] > recent.iloc[i-1] and recent.iloc[i] > recent.iloc[i+1]:
            resistance.append(recent.iloc[i])
        if recent.iloc[i] < recent.iloc[i-1] and recent.iloc[i] < recent.iloc[i+1]:
            support.append(recent.iloc[i])
    
    # Use high/low for better levels
    for i in range(2, len(highs) - 2):
        if highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i+1]:
            resistance.append(highs.iloc[i])
        if lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i+1]:
            support.append(lows.iloc[i])
    
    return {
        "resistance": sorted(list(set([round(r, 2) for r in resistance])), reverse=True)[:3],
        "support": sorted(list(set([round(s, 2) for s in support])))[:3],
    }


def full_technical_analysis(symbol: str) -> dict:
    """Run complete technical analysis on a stock."""
    try:
        df = get_history(symbol, period="1y")
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data for technical analysis"}
        
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        
        # Volume analysis
        avg_volume = volume.tail(20).mean()
        recent_volume = volume.iloc[-1]
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        result = {
            "symbol": symbol.upper(),
            "current_price": round(close.iloc[-1], 2),
            "rsi_14": round(calculate_rsi(close).iloc[-1], 1),
            "macd": calculate_macd(close),
            "bollinger": calculate_bollinger_bands(close),
            "moving_averages": calculate_sma_ema(close),
            "atr_14": calculate_atr(high, low, close),
            "support_resistance": find_support_resistance(close, high, low),
            "volume": {
                "current": int(recent_volume),
                "avg_20d": int(avg_volume),
                "ratio": round(volume_ratio, 2),
                "signal": (
                    "High volume (interest)" if volume_ratio > 1.5
                    else "Low volume (lack of interest)" if volume_ratio < 0.5
                    else "Normal volume"
                ),
            },
        }
        
        # Generate signals
        signals = []
        rsi = result["rsi_14"]
        if rsi > 70:
            signals.append("⚠️ RSI overbought (>70)")
        elif rsi < 30:
            signals.append("✅ RSI oversold (<30) - Potential buy zone")
        
        macd = result["macd"]
        if macd["trend"] == "bullish":
            signals.append("📈 MACD bullish crossover")
        else:
            signals.append("📉 MACD bearish")
        
        bb = result["bollinger"]
        if "Oversold" in bb["signal"]:
            signals.append("✅ Price near lower Bollinger Band")
        elif "Overbought" in bb["signal"]:
            signals.append("⚠️ Price near upper Bollinger Band")
        
        ma = result["moving_averages"]
        if ma.get("above_sma_200"):
            signals.append("✅ Above 200-day SMA (long-term uptrend)")
        else:
            signals.append("📉 Below 200-day SMA (long-term downtrend)")
        
        if ma.get("golden_cross"):
            signals.append("✅ Golden Cross (50 SMA > 200 SMA)")
        
        result["signals"] = signals
        
        # Overall technical rating
        bullish_count = sum(1 for s in signals if "✅" in s or "📈" in s)
        bearish_count = sum(1 for s in signals if "⚠️" in s or "📉" in s)
        
        if bullish_count > bearish_count + 2:
            result["rating"] = "STRONG BUY"
        elif bullish_count > bearish_count:
            result["rating"] = "BUY"
        elif bearish_count > bullish_count + 2:
            result["rating"] = "STRONG SELL"
        elif bearish_count > bullish_count:
            result["rating"] = "SELL"
        else:
            result["rating"] = "NEUTRAL"
        
        return result
        
    except Exception as e:
        return {"error": f"Technical analysis failed: {e}"}
