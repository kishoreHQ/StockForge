"""StockForge Data Layer - FII/DII flow data from NSE."""
import requests
from datetime import datetime


def get_fii_dii_daily(date: str = None) -> dict:
    """Get FII/DII activity for a specific date from NSE."""
    if date is None:
        date = datetime.now().strftime("%d-%b-%Y")
    
    url = f"https://www.nseindia.com/api/equity-reports?index=equities&data=fiidiiActivityHistorical&date={date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return _parse_fii_dii(data, date)
    except Exception:
        pass
    
    # Fallback: return placeholder with interpretation guide
    return {
        "date": date,
        "source": "nseindia.com (fallback - manual lookup needed)",
        "url": f"https://www.nseindia.com/reports/fii-dii",
        "note": "NSE requires session cookies. Use browser or run during market hours.",
        "interpretation_guide": {
            "fii_buy > fii_sell": "Bullish - foreign money flowing in",
            "fii_sell > fii_buy": "Bearish - foreign money flowing out",
            "dii_buy > dii_sell": "Domestic institutions supporting market",
            "consecutive_fii_selling": "Risk-off sentiment, watch for support levels",
            "fii_buying_small_caps": "Risk-on, broad market rally likely",
        }
    }


def _parse_fii_dii(data: dict, date: str) -> dict:
    """Parse FII/DII data from NSE response."""
    result = {"date": date, "source": "nseindia.com"}
    
    try:
        records = data.get("data", [])
        for record in records:
            category = record.get("category", "")
            if "FII" in category.upper() or "FOREIGN" in category.upper():
                result["fii"] = {
                    "buy_cr": record.get("buyAmount", 0),
                    "sell_cr": record.get("sellAmount", 0),
                    "net_cr": record.get("netAmount", 0),
                }
            elif "DII" in category.upper() or "DOMESTIC" in category.upper():
                result["dii"] = {
                    "buy_cr": record.get("buyAmount", 0),
                    "sell_cr": record.get("sellAmount", 0),
                    "net_cr": record.get("netAmount", 0),
                }
    except Exception:
        result["note"] = "Could not parse FII/DII data"
    
    return result


def interpret_flows(fii_net: float, dii_net: float) -> str:
    """Interpret FII/DII flows for investment decisions."""
    signals = []
    
    if fii_net > 0:
        signals.append(f"🟢 FII bought ₹{fii_net:.0f}Cr - Foreign money flowing in")
    else:
        signals.append(f"🔴 FII sold ₹{abs(fii_net):.0f}Cr - Foreign money flowing out")
    
    if dii_net > 0:
        signals.append(f"🟢 DII bought ₹{dii_net:.0f}Cr - Domestic support")
    else:
        signals.append(f"🔴 DII sold ₹{abs(dii_net):.0f}Cr - Domestic profit booking")
    
    # Combined interpretation
    total_net = fii_net + dii_net
    if total_net > 5000:
        signals.append("💪 Strong net inflow - Bullish for market")
    elif total_net < -5000:
        signals.append("⚠️ Strong net outflow - Caution warranted")
    
    if fii_net > 0 and dii_net > 0:
        signals.append("✅ Both FII and DII buying - Very bullish")
    elif fii_net < 0 and dii_net < 0:
        signals.append("🚨 Both FII and DII selling - Risk-off environment")
    elif fii_net < 0 and dii_net > 0:
        signals.append("🔄 FIIs selling but DIIs absorbing - Domestic resilience")
    
    return "\n".join(signals)
