"""StockForge Screeners - Technical and fundamental stock screening."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_index_constituents, get_batch_quotes, get_history
from analysis.technical import calculate_rsi, calculate_sma_ema
from analysis.fundamental import score_fundamentals
import pandas as pd
import numpy as np


def screen_vcp(universe: list = None) -> list:
    """Screen for Volatility Contraction Pattern (Mark Minervini style)."""
    if universe is None:
        universe = get_index_constituents("nifty500")
    
    results = []
    
    for symbol in universe:
        try:
            df = get_history(symbol, period="1y")
            if df.empty or len(df) < 200:
                continue
            
            close = df["Close"]
            volume = df["Volume"]
            current = close.iloc[-1]
            
            # Trend template: stock above 150-day and 200-day MA
            sma_150 = close.rolling(150).mean().iloc[-1]
            sma_200 = close.rolling(200).mean().iloc[-1]
            
            if current <= sma_150 or current <= sma_200:
                continue
            
            # 200-day MA trending up
            sma_200_20ago = close.rolling(200).mean().iloc[-20]
            if sma_200 <= sma_200_20ago:
                continue
            
            # Stock up at least 25% from 52-week low
            low_52w = close.tail(252).min()
            if current < low_52w * 1.25:
                continue
            
            # Within 15% of 52-week high
            high_52w = close.tail(252).max()
            if current < high_52w * 0.85:
                continue
            
            # RSI in normal range (not overbought)
            rsi = calculate_rsi(close).iloc[-1]
            if rsi > 75:
                continue
            
            # Volume dry-up in last 5 days vs average
            avg_vol_20 = volume.tail(20).mean()
            recent_vol = volume.tail(5).mean()
            vol_ratio = recent_vol / avg_vol_20 if avg_vol_20 > 0 else 1
            
            # Price contraction (low volatility recently)
            recent_returns = close.pct_change().tail(20)
            volatility = recent_returns.std()
            
            # Score
            score = 0
            if current > sma_200 * 1.3:
                score += 2  # Strong uptrend
            if vol_ratio < 0.7:
                score += 2  # Volume drying up
            if volatility < 0.02:
                score += 2  # Tight contraction
            
            if score >= 4:
                results.append({
                    "symbol": symbol,
                    "price": round(current, 2),
                    "vs_52w_high_pct": round((current / high_52w - 1) * 100, 1),
                    "rsi": round(rsi, 1),
                    "volume_ratio": round(vol_ratio, 2),
                    "volatility": round(volatility, 4),
                    "vcp_score": score,
                })
        except Exception:
            continue
    
    results.sort(key=lambda x: x["vcp_score"], reverse=True)
    return results


def screen_fundamental_quality(universe: list = None, min_score: int = 60) -> list:
    """Screen for fundamentally strong stocks."""
    if universe is None:
        universe = get_index_constituents("nifty50")
    
    results = []
    
    for symbol in universe:
        try:
            scored = score_fundamentals(symbol)
            if "error" in scored:
                continue
            
            if scored["score"] >= min_score:
                results.append({
                    "symbol": symbol,
                    "score": scored["score"],
                    "tier": scored["tier"],
                    "pe": scored["ratios"].get("pe"),
                    "roce": scored["ratios"].get("roce"),
                    "roe": scored["ratios"].get("roe"),
                    "debt_to_equity": scored["ratios"].get("debt_to_equity"),
                    "signals": scored["signals"][:3],
                })
        except Exception:
            continue
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def screen_breakout(universe: list = None) -> list:
    """Screen for stocks near breakout levels."""
    if universe is None:
        universe = get_index_constituents("nifty500")[:100]
    
    results = []
    
    for symbol in universe:
        try:
            df = get_history(symbol, period="3mo")
            if df.empty or len(df) < 60:
                continue
            
            close = df["Close"]
            volume = df["Volume"]
            current = close.iloc[-1]
            
            # Recent high (20-day)
            high_20 = close.tail(20).max()
            
            # Within 5% of 20-day high
            if current >= high_20 * 0.95 and current <= high_20 * 1.02:
                # Volume surge
                avg_vol = volume.tail(20).mean()
                recent_vol = volume.iloc[-1]
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
                
                # RSI strength
                rsi = calculate_rsi(close).iloc[-1]
                
                # Above key MAs
                ma_data = calculate_sma_ema(close)
                above_ma = sum([
                    ma_data.get("above_sma_20", False),
                    ma_data.get("above_sma_50", False),
                    ma_data.get("above_sma_200", False),
                ])
                
                if vol_ratio > 1.2 and above_ma >= 2:
                    results.append({
                        "symbol": symbol,
                        "price": round(current, 2),
                        "near_20d_high": round(high_20, 2),
                        "distance_pct": round((current / high_20 - 1) * 100, 1),
                        "volume_ratio": round(vol_ratio, 2),
                        "rsi": round(rsi, 1),
                        "above_ma_count": above_ma,
                    })
        except Exception:
            continue
    
    results.sort(key=lambda x: x["volume_ratio"], reverse=True)
    return results


def run_screen(screen_type: str = "fundamental", universe: list = None) -> list:
    """Run specified screen type."""
    if screen_type == "vcp":
        return screen_vcp(universe)
    elif screen_type == "fundamental":
        return screen_fundamental_quality(universe)
    elif screen_type == "breakout":
        return screen_breakout(universe)
    elif screen_type == "all":
        return {
            "vcp": screen_vcp(universe),
            "fundamental": screen_fundamental_quality(universe),
            "breakout": screen_breakout(universe),
        }
    else:
        return screen_fundamental_quality(universe)
