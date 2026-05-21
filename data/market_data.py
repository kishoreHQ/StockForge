"""StockForge Data Layer - Market data fetching from NSE/BSE."""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def nse_symbol(symbol: str) -> str:
    """Convert NSE symbol to yfinance format."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        return f"{symbol}.NS"
    return symbol


def get_quote(symbol: str) -> dict:
    """Get current quote for a stock."""
    ticker = yf.Ticker(nse_symbol(symbol))
    info = ticker.fast_info
    hist = ticker.history(period="5d")
    
    if hist.empty:
        return {"error": f"No data for {symbol}"}
    
    close = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else close
    change = close - prev_close
    change_pct = (change / prev_close) * 100
    
    # 52-week ranges from history
    hist_1y = ticker.history(period="1y")
    w52_high = round(hist_1y["High"].max(), 2) if not hist_1y.empty else 0
    w52_low = round(hist_1y["Low"].min(), 2) if not hist_1y.empty else 0
    
    return {
        "symbol": symbol.upper(),
        "price": round(close, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "open": round(hist["Open"].iloc[-1], 2),
        "high": round(hist["High"].iloc[-1], 2),
        "low": round(hist["Low"].iloc[-1], 2),
        "volume": int(hist["Volume"].iloc[-1]),
        "prev_close": round(prev_close, 2),
        "52w_high": w52_high,
        "52w_low": w52_low,
        "market_cap": getattr(info, 'market_cap', None),
        "pe_ratio": getattr(info, 'trailing_pe', None),
    }


def get_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Get historical OHLCV data."""
    ticker = yf.Ticker(nse_symbol(symbol))
    df = ticker.history(period=period)
    return df


def get_index(index_name: str = "^NSEI") -> dict:
    """Get index quote. Default: NIFTY 50."""
    ticker = yf.Ticker(index_name)
    hist = ticker.history(period="5d")
    
    if hist.empty:
        return {"error": f"No data for {index_name}"}
    
    close = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else close
    change = close - prev_close
    change_pct = (change / prev_close) * 100
    
    return {
        "name": index_name,
        "value": round(close, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "high": round(hist["High"].iloc[-1], 2),
        "low": round(hist["Low"].iloc[-1], 2),
        "volume": int(hist["Volume"].iloc[-1]),
    }


def get_top_movers(universe: list = None, direction: str = "both", limit: int = 10) -> dict:
    """Find top gainers/losers in a universe of stocks."""
    if universe is None:
        universe = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
                    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE",
                    "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
                    "TITAN", "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "WIPRO"]
    
    results = []
    for sym in universe:
        try:
            q = get_quote(sym)
            if "error" not in q:
                results.append(q)
        except Exception:
            continue
    
    if not results:
        return {"gainers": [], "losers": []}
    
    results.sort(key=lambda x: x["change_pct"], reverse=True)
    
    return {
        "gainers": results[:limit],
        "losers": results[-limit:][::-1] if direction == "both" else [],
        "all": results,
    }


def get_batch_quotes(symbols: list) -> list:
    """Get quotes for multiple stocks efficiently."""
    results = []
    for sym in symbols:
        try:
            q = get_quote(sym)
            if "error" not in q:
                results.append(q)
        except Exception:
            continue
    return results


def get_index_constituents(index: str = "nifty50") -> list:
    """Return NIFTY 50 constituents (hardcoded, updates periodically)."""
    nifty50 = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BHARTIARTL", "BPCL",
        "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
        "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO",
        "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL",
        "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
        "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM",
        "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO",
        "UPL", "WIPRO", "LTIM"
    ]
    
    nifty_next50 = [
        "ABB", "AMBUJACEM", "BANKBARODA", "BOSCHLTD", "CANBK", "CHOLAFIN",
        "DABUR", "DLF", "GAIL", "GODREJCP", "HAVELLS", "IDFCFIRSTB", "INDIGO",
        "IOC", "IRFC", "JINDALSTEL", "LUPIN", "MANAPPURAM", "MUTHOOTFIN",
        "NAUKRI", "PIDILITIND", "PNB", "SBICARD", "SIEMENS", "SRF",
        "TORNTPHARM", "TRENT", "VBL", "VEDL", "ZYDUSLIFE",
        "ADANIGREEN", "ADANIENT", "BIOCON", "COLPAL", "CONCOR",
        "CROMPTON", "CUB", "ESCORTS", "GLAND", "IGL",
        "L&TFH", "MCX", "NHPC", "OBEROIRLTY", "PERSISTENT",
        "POLICYBZR", "RDY", "SHREECEM", "SOLARINDS", "TORNTPOWER"
    ]
    
    index = index.lower().replace(" ", "").replace("_", "")
    if index == "nifty50":
        return nifty50
    elif index in ("nifty500", "nifty", "all"):
        return list(set(nifty50 + nifty_next50))
    elif index == "next50":
        return nifty_next50
    return nifty50
