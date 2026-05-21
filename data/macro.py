"""StockForge Data Layer - Macro data: India VIX, RBI rates, G-Sec yields."""
import yfinance as yf
from datetime import datetime


def get_india_vix() -> dict:
    """Get India VIX (volatility index)."""
    try:
        ticker = yf.Ticker("^INDIAVIX")
        hist = ticker.history(period="1mo")
        
        if hist.empty:
            return {"error": "No VIX data available"}
        
        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = current - prev
        
        # VIX interpretation
        if current < 12:
            level = "LOW - Complacency, low fear"
            signal = "Markets comfortable, but watch for sudden spikes"
        elif current < 18:
            level = "MODERATE - Normal range"
            signal = "Healthy market conditions"
        elif current < 25:
            level = "ELEVATED - Caution"
            signal = "Increased uncertainty, consider hedging"
        else:
            level = "HIGH - Fear/Stress"
            signal = "High volatility - opportunities for value buyers but risky"
        
        return {
            "vix": round(current, 2),
            "change": round(change, 2),
            "change_pct": round((change / prev) * 100, 2) if prev else 0,
            "level": level,
            "signal": signal,
        }
    except Exception as e:
        return {"error": f"VIX fetch failed: {e}"}


def get_rbi_rates() -> dict:
    """Get key RBI policy rates (hardcoded, updated periodically)."""
    return {
        "source": "RBI (as of latest policy)",
        "last_updated": "Feb 2026",
        "rates": {
            "repo_rate": {"value": 6.25, "unit": "%", "description": "Rate at which RBI lends to banks"},
            "reverse_repo": {"value": 3.35, "unit": "%", "description": "Rate at which RBI borrows from banks"},
            "msf": {"value": 6.50, "unit": "%", "description": "Marginal Standing Facility rate"},
            "bank_rate": {"value": 6.50, "unit": "%", "description": "Rate for long-term lending to banks"},
            "crr": {"value": 4.0, "unit": "%", "description": "Cash Reserve Ratio"},
            "slr": {"value": 18.0, "unit": "%", "description": "Statutory Liquidity Ratio"},
        },
        "interpretation": {
            "rate_cut": "Bullish for equities - cheaper money, more liquidity",
            "rate_hike": "Bearish short-term - tighter money, but shows inflation control",
            "status_quo": "Neutral - markets focus on other factors",
        }
    }


def get_market_indicators() -> dict:
    """Get key market health indicators."""
    indicators = {}
    
    # India VIX
    vix = get_india_vix()
    indicators["vix"] = vix
    
    # USD/INR
    try:
        usdinr = yf.Ticker("USDINR=X")
        hist = usdinr.history(period="1mo")
        if not hist.empty:
            indicators["usd_inr"] = {
                "rate": round(hist["Close"].iloc[-1], 4),
                "change": round(hist["Close"].iloc[-1] - hist["Close"].iloc[-2], 4),
            }
    except Exception:
        pass
    
    # 10-Year G-Sec proxy
    try:
        gsec = yf.Ticker("IN10YTDM=Y")
        hist = gsec.history(period="1mo")
        if not hist.empty:
            indicators["gsec_10y"] = {
                "yield": round(hist["Close"].iloc[-1], 2),
                "unit": "%",
            }
    except Exception:
        pass
    
    return indicators
