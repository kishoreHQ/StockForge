"""StockForge Data Layer - Fundamental data from screener.in and other sources."""
import requests
from bs4 import BeautifulSoup
import re
import time


def scrape_screener(symbol: str) -> dict:
    """Scrape key fundamentals from screener.in."""
    url = f"https://www.screener.in/company/{symbol.upper()}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        return {"error": f"Failed to fetch: {e}"}
    
    data = {"symbol": symbol.upper(), "source": "screener.in"}
    
    # Extract price and market cap from header
    header = soup.find("div", class_="company-header")
    if header:
        price_el = header.find("h2", class_="company-price")
        if price_el:
            price_text = price_el.get_text().strip()
            match = re.search(r"₹\s*([\d,]+\.?\d*)", price_text)
            if match:
                data["current_price"] = float(match.group(1).replace(",", ""))
    
    # Extract key ratios table
    ratios = {}
    for table in soup.find_all("table", class_="data-table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower().replace(" ", "_")
                val_text = cells[-1].get_text(strip=True)
                # Try to parse numeric value
                try:
                    val = val_text.replace(",", "").replace("%", "").replace("₹", "").strip()
                    if val:
                        ratios[key] = float(val) if val.replace(".", "").replace("-", "").isdigit() else val
                except (ValueError, IndexError):
                    ratios[key] = val_text
    
    data["ratios"] = ratios
    
    # Extract shareholding pattern
    shareholding = {}
    sh_tables = soup.find_all("table", class_="data-table")
    for table in sh_tables:
        header_row = table.find("tr")
        if header_row:
            header_text = header_row.get_text().lower()
            if "shareholding" in header_text or "pattern" in header_text:
                rows = table.find_all("tr")[1:]  # skip header
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        holder = cells[0].get_text(strip=True)
                        try:
                            pct = float(cells[-1].get_text(strip=True).replace("%", ""))
                            shareholding[holder] = pct
                        except (ValueError, IndexError):
                            pass
    
    if shareholding:
        data["shareholding"] = shareholding
    
    # Extract key metrics from company info
    info_items = soup.find_all("li")
    for item in info_items:
        text = item.get_text(strip=True).lower()
        if "market cap" in text:
            match = re.search(r"₹\s*([\d,.]+)\s*(cr|lakh)", text)
            if match:
                val = float(match.group(1).replace(",", ""))
                data["market_cap_cr"] = val if match.group(2) == "cr" else val / 100000
    
    return data


def get_key_ratios(symbol: str) -> dict:
    """Get key investment ratios with interpretation."""
    raw = scrape_screener(symbol)
    if "error" in raw:
        return raw
    
    ratios = raw.get("ratios", {})
    result = {
        "symbol": symbol.upper(),
        "pe": ratios.get("price/earnings", ratios.get("pe ratio", ratios.get("pe", "N/A"))),
        "pb": ratios.get("price/book", ratios.get("pb ratio", ratios.get("pb", "N/A"))),
        "debt_to_equity": ratios.get("debt to equity", ratios.get("debt/equity", "N/A")),
        "roe": ratios.get("return on equity", ratios.get("roe", ratios.get("roce", "N/A"))),
        "roce": ratios.get("return on capital employed", ratios.get("roce", "N/A")),
        "profit_margin": ratios.get("net profit margin", ratios.get("operating margin", "N/A")),
        "dividend_yield": ratios.get("dividend yield", "N/A"),
        "eps": ratios.get("earnings per share", ratios.get("eps", "N/A")),
        "book_value": ratios.get("book value", ratios.get("bvps", "N/A")),
    }
    
    # Investment quality assessment
    quality = []
    pe = result["pe"]
    if isinstance(pe, (int, float)):
        if pe < 15:
            quality.append("✅ Low PE (potentially undervalued)")
        elif pe > 50:
            quality.append("⚠️ High PE (growth priced in)")
    
    debt = result["debt_to_equity"]
    if isinstance(debt, (int, float)):
        if debt < 0.5:
            quality.append("✅ Low debt")
        elif debt > 2:
            quality.append("⚠️ High debt")
    
    roce = result["roce"]
    if isinstance(roce, (int, float)):
        if roce > 20:
            quality.append("✅ High ROCE (quality business)")
        elif roce < 10:
            quality.append("⚠️ Low ROCE")
    
    roe = result["roe"]
    if isinstance(roe, (int, float)):
        if roe > 15:
            quality.append("✅ Good ROE")
    
    result["quality_signals"] = quality if quality else ["ℹ️ Insufficient data for quality assessment"]
    
    return result


def get_shareholding(symbol: str) -> dict:
    """Get shareholding pattern."""
    raw = scrape_screener(symbol)
    if "error" in raw:
        return raw
    
    return {
        "symbol": symbol.upper(),
        "shareholding": raw.get("shareholding", {}),
    }
