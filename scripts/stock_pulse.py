#!/usr/bin/python3.12
"""StockPulse — 4x daily market intelligence pulses for Telegram delivery."""

import sys
import json
import time
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────
PULSE_TYPES = {
    "pre-market": {
        "title": "🌅 PRE-MARKET PULSE",
        "time": "8:00 AM IST",
        "focus": "global_cues, levels, overnight_news",
    },
    "mid-day": {
        "title": "☀️ MID-DAY PULSE",
        "time": "11:30 AM IST",
        "focus": "live_market, movers, sectors",
    },
    "pre-close": {
        "title": "📉 PRE-CLOSE PULSE",
        "time": "2:30 PM IST",
        "focus": "oi_shifts, european_open, momentum",
    },
    "post-market": {
        "title": "🔔 POST-MARKET WRAP",
        "time": "4:00 PM IST",
        "focus": "closing_data, fii_dii, next_day",
    },
}

# ── Data Fetchers ───────────────────────────────────────────────────

def safe_fetch(fetcher, timeout=12, default=None):
    """Run a fetcher with timeout, return default on failure."""
    try:
        import signal
        def handler(s, f):
            raise TimeoutError("fetch timeout")
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)
        result = fetcher()
        signal.alarm(0)
        return result
    except Exception:
        signal.alarm(0)
        return default

def get_indices():
    """Get key Indian indices."""
    import yfinance as yf
    results = {}
    symbols = {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "NIFTY BANK": "^NSEBANK",
        "NIFTY IT": "^CNXIT",
        "NIFTY FINANCIAL": "^CNXFIN",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY REALTY": "^CNXREALTY",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY PHARMA": "^CNXPHARMA",
        "INDIA VIX": "^INDIAVIX",
        "USD/INR": "USDINR=X",
    }
    for name, sym in symbols.items():
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = info.last_price
            prev = info.previous_close
            chg = ((price - prev) / prev * 100) if prev else 0
            results[name] = {"price": price, "change": chg}
        except:
            results[name] = None
    return results

def get_global_cues():
    """Get global market indices."""
    import yfinance as yf
    results = {}
    symbols = {
        "DOW": "^DJI",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Nikkei": "^N225",
        "Hang Seng": "^HSI",
        "FTSE": "^FTSE",
        "Brent Crude": "BZ=F",
        "Gold": "GC=F",
        "US 10Y Yield": "TNX",
    }
    for name, sym in symbols.items():
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = info.last_price
            prev = info.previous_close
            chg = ((price - prev) / prev * 100) if prev else 0
            results[name] = {"price": price, "change": chg}
        except:
            results[name] = None
    return results

def get_key_stocks():
    """Get heavyweight stock prices."""
    import yfinance as yf
    results = {}
    symbols = {
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "ICICIBANK": "ICICIBANK.NS",
        "SBIN": "SBIN.NS",
        "BHARTIARTL": "BHARTIARTL.NS",
        "ITC": "ITC.NS",
        "WIPRO": "WIPRO.NS",
        "HCLTECH": "HCLTECH.NS",
        "ADANIENT": "ADANIENT.NS",
        "KOTAKBANK": "KOTAKBANK.NS",
        "LT": "LT.NS",
        "AXISBANK": "AXISBANK.NS",
    }
    for name, sym in symbols.items():
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = info.last_price
            prev = info.previous_close
            chg = ((price - prev) / prev * 100) if prev else 0
            vol = info.last_volume
            results[name] = {"price": price, "change": chg, "volume": vol}
        except:
            results[name] = None
    return results

def get_fii_dii_text():
    """Scrape FII/DII from MoneyControl."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://www.moneycontrol.com/stocksmarketsindia/fiidii.html",
            headers=headers, timeout=8
        )
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # Find FII/DII table
        for table in soup.find_all("table"):
            text = table.get_text()
            if "FII" in text and "DII" in text:
                rows = []
                for row in table.find_all("tr")[:6]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if cells:
                        rows.append(" | ".join(cells))
                return "\n".join(rows) if rows else None
        return None
    except:
        return None

def format_change(val):
    """Format change with emoji."""
    if val is None:
        return "—"
    if val > 0.5:
        emoji = "🟢"
    elif val > 0:
        emoji = "🟩"
    elif val < -0.5:
        emoji = "🔴"
    elif val < 0:
        emoji = "🟥"
    else:
        emoji = "⚪"
    return f"{emoji} {val:+.2f}%"

# ── Pulse Generators ────────────────────────────────────────────────

def pre_market_pulse(indices, global_cues, fii_dii):
    """Generate pre-market briefing."""
    lines = []
    lines.append("🌅 PRE-MARKET PULSE — 8:00 AM IST")
    lines.append("=" * 40)
    lines.append("")
    lines.append("**Global Cues (Overnight)**")

    for name, data in global_cues.items():
        if data:
            price_str = f"{data['price']:,.2f}" if "Yield" not in name else f"{data['price']:.3f}%"
            chg = format_change(data["change"])
            lines.append(f"  • {name}: {price_str}  {chg}")

    lines.append("")
    lines.append("**Indian Indices (Prev Close)**")
    key_indices = ["NIFTY 50", "SENSEX", "NIFTY BANK", "NIFTY IT", "INDIA VIX", "USD/INR"]
    for name in key_indices:
        data = indices.get(name)
        if data:
            unit = "%" if name == "INDIA VIX" else ""
            lines.append(f"  • {name}: {data['price']:,.2f}{unit}  {format_change(data['change'])}")

    if fii_dii:
        lines.append("")
        lines.append("**FII/DII Activity**")
        for row in fii_dii.split("\n")[:3]:
            lines.append(f"  {row}")

    lines.append("")
    lines.append("**Today's Key Levels — NIFTY 50**")
    nifty = indices.get("NIFTY 50")
    if nifty:
        close = nifty["price"]
        lines.append(f"  Prev Close: {close:,.2f}")
        lines.append(f"  Resistance: {close + 140:,.0f} | {close + 280:,.0f}")
        lines.append(f"  Support:    {close - 100:,.0f} | {close - 250:,.0f}")

    lines.append("")
    lines.append("📌 _Watch for opening gap vs GIFT Nifty trend_")
    return "\n".join(lines)


def mid_day_pulse(indices, stocks, global_cues):
    """Generate mid-day market check."""
    lines = []
    lines.append("☀️ MID-DAY PULSE — 11:30 AM IST")
    lines.append("=" * 40)
    lines.append("")
    lines.append("**Live Indices**")
    for name in ["NIFTY 50", "SENSEX", "NIFTY BANK", "NIFTY IT", "INDIA VIX"]:
        data = indices.get(name)
        if data:
            lines.append(f"  • {name}: {data['price']:,.2f}  {format_change(data['change'])}")

    lines.append("")
    lines.append("**Top Movers (Heavyweights)**")

    gainers = []
    losers = []
    for name, data in stocks.items():
        if data and data.get("change") is not None:
            if data["change"] > 0.3:
                gainers.append((name, data["price"], data["change"]))
            elif data["change"] < -0.3:
                losers.append((name, data["price"], data["change"]))

    gainers.sort(key=lambda x: x[2], reverse=True)
    losers.sort(key=lambda x: x[2])

    if gainers:
        lines.append("  🟢 Gainers:")
        for name, price, chg in gainers[:5]:
            lines.append(f"    {name}: ₹{price:,.1f}  {format_change(chg)}")

    if losers:
        lines.append("  🔴 Losers:")
        for name, price, chg in losers[:5]:
            lines.append(f"    {name}: ₹{price:,.1f}  {format_change(chg)}")

    lines.append("")
    lines.append("**Volume Leaders**")
    vol_stocks = [(n, d) for n, d in stocks.items() if d and d.get("volume") and d["volume"] > 5_000_000]
    vol_stocks.sort(key=lambda x: x[1]["volume"], reverse=True)
    for name, data in vol_stocks[:5]:
        vol_str = f"{data['volume']/1e6:.1f}M"
        lines.append(f"  • {name}: {vol_str} vol  {format_change(data.get('change'))}")

    eu = global_cues.get("FTSE")
    if eu:
        lines.append("")
        lines.append(f"**Europe FTSE**: {eu['price']:,.2f}  {format_change(eu['change'])}")

    return "\n".join(lines)


def pre_close_pulse(indices, stocks, global_cues):
    """Generate pre-close momentum check."""
    lines = []
    lines.append("📉 PRE-CLOSE PULSE — 2:30 PM IST")
    lines.append("=" * 40)
    lines.append("")
    lines.append("**Current Market Position**")
    for name in ["NIFTY 50", "SENSEX", "NIFTY BANK", "NIFTY IT"]:
        data = indices.get(name)
        if data:
            lines.append(f"  • {name}: {data['price']:,.2f}  {format_change(data['change'])}")

    vix = indices.get("INDIA VIX")
    if vix:
        vix_status = "easing" if vix["change"] < 0 else "rising"
        lines.append(f"  • INDIA VIX: {vix['price']:.2f} ({vix_status})")

    lines.append("")
    lines.append("**Final Hour Setup**")
    nifty = indices.get("NIFTY 50")
    if nifty:
        close = nifty["price"]
        chg = nifty["change"]
        if chg > 0.5:
            sentiment = "🟢 Bullish momentum"
        elif chg > 0:
            sentiment = "🟩 Mildly positive"
        elif chg > -0.5:
            sentiment = "🟥 Mildly negative"
        else:
            sentiment = "🔴 Bearish pressure"
        lines.append(f"  Sentiment: {sentiment}")
        lines.append(f"  Range today: ~{close - abs(chg*close/100)*0.3:,.0f} — {close + abs(chg*close/100)*0.3:,.0f}")

    eu = global_cues.get("FTSE")
    if eu:
        lines.append(f"  Europe (FTSE): {format_change(eu['change'])}")

    us = global_cues.get("NASDAQ")
    if us:
        lines.append(f"  US Futures cue: NASDAQ prev {format_change(us['change'])}")

    lines.append("")
    lines.append("📌 _Watch for last-30-min volume surge & OI rollover_")
    return "\n".join(lines)


def post_market_pulse(indices, stocks, fii_dii):
    """Generate post-market wrap with next-day outlook."""
    lines = []
    lines.append("🔔 POST-MARKET WRAP — 4:00 PM IST")
    lines.append("=" * 40)
    lines.append("")
    lines.append("**Closing Summary**")
    for name in ["NIFTY 50", "SENSEX", "NIFTY BANK", "NIFTY IT", "INDIA VIX", "USD/INR"]:
        data = indices.get(name)
        if data:
            lines.append(f"  • {name}: {data['price']:,.2f}  {format_change(data['change'])}")

    lines.append("")
    lines.append("**Sector Leaders & Laggards**")
    sectors = ["NIFTY BANK", "NIFTY IT", "NIFTY FINANCIAL", "NIFTY METAL", "NIFTY REALTY", "NIFTY AUTO", "NIFTY PHARMA"]
    for name in sectors:
        data = indices.get(name)
        if data:
            icon = "🟢" if data["change"] > 0.3 else ("🔴" if data["change"] < -0.3 else "⚪")
            lines.append(f"  {icon} {name}: {format_change(data['change'])}")

    if fii_dii:
        lines.append("")
        lines.append("**FII/DII (Today)**")
        for row in fii_dii.split("\n")[:4]:
            lines.append(f"  {row}")

    nifty = indices.get("NIFTY 50")
    if nifty:
        close = nifty["price"]
        lines.append("")
        lines.append("**Next Day Levels**")
        lines.append(f"  Support:    {close - 80:,.0f} | {close - 200:,.0f}")
        lines.append(f"  Resistance: {close + 80:,.0f} | {close + 200:,.0f}")

    lines.append("")
    lines.append("_Full intelligence at 8:00 AM tomorrow_")
    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: stock_pulse.py <pre-market|mid-day|pre-close|post-market>")
        sys.exit(1)

    pulse_type = sys.argv[1]
    if pulse_type not in PULSE_TYPES:
        print(f"Unknown pulse type: {pulse_type}")
        print(f"Available: {', '.join(PULSE_TYPES.keys())}")
        sys.exit(1)

    info = PULSE_TYPES[pulse_type]
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M UTC")

    # Fetch all data upfront
    indices = safe_fetch(get_indices, timeout=25) or {}
    global_cues = safe_fetch(get_global_cues, timeout=25) or {}
    stocks = safe_fetch(get_key_stocks, timeout=30) or {}
    fii_dii = safe_fetch(get_fii_dii_text, timeout=12)

    # Generate pulse
    if pulse_type == "pre-market":
        content = pre_market_pulse(indices, global_cues, fii_dii)
    elif pulse_type == "mid-day":
        content = mid_day_pulse(indices, stocks, global_cues)
    elif pulse_type == "pre-close":
        content = pre_close_pulse(indices, stocks, global_cues)
    elif pulse_type == "post-market":
        content = post_market_pulse(indices, stocks, fii_dii)

    header = f"**StockPulse** — {now}\n"
    print(header + content)


if __name__ == "__main__":
    main()
