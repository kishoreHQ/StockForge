"""StockForge Analysis - Valuation estimates."""
from data.fundamentals import get_key_ratios
from data.market_data import get_quote


def dcf_estimate(symbol: str, growth_rate: float = 12, terminal_growth: float = 4,
                 discount_rate: float = 12, years: int = 5) -> dict:
    """Simple DCF valuation estimate."""
    ratios = get_key_ratios(symbol)
    quote = get_quote(symbol)
    
    if "error" in ratios or "error" in quote:
        return {"error": "Insufficient data for DCF"}
    
    eps = ratios.get("eps")
    pe = ratios.get("pe")
    
    if not isinstance(eps, (int, float)) or eps <= 0:
        return {"error": "No EPS data available for DCF"}
    
    # Project future EPS
    future_eps = []
    current_eps = eps
    for i in range(years):
        current_eps *= (1 + growth_rate / 100)
        future_eps.append(current_eps)
    
    # Terminal value
    terminal_eps = future_eps[-1] * (1 + terminal_growth / 100)
    terminal_value = terminal_eps / (discount_rate / 100 - terminal_growth / 100)
    
    # Discount to present
    present_values = []
    for i, eps in enumerate(future_eps):
        pv = eps / ((1 + discount_rate / 100) ** (i + 1))
        present_values.append(pv)
    
    terminal_pv = terminal_value / ((1 + discount_rate / 100) ** years)
    
    intrinsic_value = sum(present_values) + terminal_pv
    
    current_price = quote["price"]
    upside = ((intrinsic_value - current_price) / current_price) * 100
    
    return {
        "symbol": symbol.upper(),
        "current_eps": round(eps, 2),
        "current_price": current_price,
        "intrinsic_value": round(intrinsic_value, 2),
        "upside_pct": round(upside, 1),
        "assumptions": {
            "growth_rate_pct": growth_rate,
            "terminal_growth_pct": terminal_growth,
            "discount_rate_pct": discount_rate,
            "projection_years": years,
        },
        "verdict": (
            "UNDERVALUED" if upside > 15
            else "FAIRLY VALUED" if -15 <= upside <= 15
            else "OVERVALUED"
        ),
    }


def pe_pb_analysis(symbol: str) -> dict:
    """Compare current PE/PB to historical ranges."""
    ratios = get_key_ratios(symbol)
    
    if "error" in ratios:
        return ratios
    
    pe = ratios.get("pe", "N/A")
    pb = ratios.get("pb", "N/A")
    
    analysis = {"symbol": symbol.upper(), "pe": pe, "pb": pb}
    
    # Sector-based benchmarks
    if isinstance(pe, (int, float)) and pe > 0:
        if pe < 15:
            analysis["pe_assessment"] = "Below market average - potential value"
            analysis["pe_score"] = 8
        elif pe < 25:
            analysis["pe_assessment"] = "Around market average"
            analysis["pe_score"] = 5
        elif pe < 50:
            analysis["pe_assessment"] = "Premium valuation - growth expected"
            analysis["pe_score"] = 3
        else:
            analysis["pe_assessment"] = "Very expensive - high expectations"
            analysis["pe_score"] = 1
    else:
        analysis["pe_assessment"] = "PE not available"
        analysis["pe_score"] = 5
    
    if isinstance(pb, (int, float)) and pb > 0:
        if pb < 2:
            analysis["pb_assessment"] = "Below book value - potential bargain"
            analysis["pb_score"] = 8
        elif pb < 4:
            analysis["pb_assessment"] = "Reasonable PB"
            analysis["pb_score"] = 5
        elif pb < 8:
            analysis["pb_assessment"] = "Premium PB"
            analysis["pb_score"] = 3
        else:
            analysis["pb_assessment"] = "Very expensive PB"
            analysis["pb_score"] = 1
    else:
        analysis["pb_assessment"] = "PB not available"
        analysis["pb_score"] = 5
    
    analysis["value_score"] = round((analysis["pe_score"] + analysis["pb_score"]) / 2, 1)
    
    return analysis
