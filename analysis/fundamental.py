"""StockForge Analysis - Fundamental analysis scoring."""
from data.fundamentals import get_key_ratios


def score_fundamentals(symbol: str) -> dict:
    """Score a stock on fundamental quality (0-100)."""
    ratios = get_key_ratios(symbol)
    if "error" in ratios:
        return ratios
    
    score = 50  # Base score
    signals = []
    risks = []
    
    # ROCE scoring (0-20 points)
    roce = ratios.get("roce", "N/A")
    if isinstance(roce, (int, float)):
        if roce >= 25:
            score += 20
            signals.append(f"Excellent ROCE: {roce}%")
        elif roce >= 18:
            score += 15
            signals.append(f"Good ROCE: {roce}%")
        elif roce >= 12:
            score += 8
            signals.append(f"Average ROCE: {roce}%")
        else:
            score -= 10
            risks.append(f"Low ROCE: {roce}%")
    else:
        signals.append("ROCE data unavailable")
    
    # ROE scoring (0-15 points)
    roe = ratios.get("roe", "N/A")
    if isinstance(roe, (int, float)):
        if roe >= 20:
            score += 15
            signals.append(f"Strong ROE: {roe}%")
        elif roe >= 15:
            score += 10
            signals.append(f"Good ROE: {roe}%")
        elif roe >= 10:
            score += 5
            signals.append(f"Moderate ROE: {roe}%")
        else:
            score -= 5
            risks.append(f"Low ROE: {roe}%")
    
    # Debt to Equity scoring (0-20 points)
    debt = ratios.get("debt_to_equity", "N/A")
    if isinstance(debt, (int, float)):
        if debt <= 0.1:
            score += 20
            signals.append(f"Nearly debt-free (D/E: {debt})")
        elif debt <= 0.5:
            score += 15
            signals.append(f"Low debt (D/E: {debt})")
        elif debt <= 1:
            score += 5
            signals.append(f"Manageable debt (D/E: {debt})")
        elif debt <= 2:
            score -= 5
            risks.append(f"Moderate debt (D/E: {debt})")
        else:
            score -= 15
            risks.append(f"High debt (D/E: {debt})")
    
    # PE ratio scoring (0-15 points)
    pe = ratios.get("pe", "N/A")
    if isinstance(pe, (int, float)) and pe > 0:
        if pe <= 15:
            score += 15
            signals.append(f"Attractive PE: {pe}")
        elif pe <= 25:
            score += 10
            signals.append(f"Reasonable PE: {pe}")
        elif pe <= 40:
            score += 3
            signals.append(f"Premium PE: {pe}")
        else:
            score -= 5
            risks.append(f"Expensive PE: {pe}")
    
    # Profit margin scoring (0-10 points)
    margin = ratios.get("profit_margin", "N/A")
    if isinstance(margin, (int, float)):
        if margin >= 20:
            score += 10
            signals.append(f"High margin: {margin}%")
        elif margin >= 10:
            score += 5
            signals.append(f"Good margin: {margin}%")
        elif margin >= 5:
            score += 2
            signals.append(f"Thin margin: {margin}%")
        else:
            score -= 5
            risks.append(f"Very thin margin: {margin}%")
    
    # Dividend yield bonus (0-5 points)
    div = ratios.get("dividend_yield", "N/A")
    if isinstance(div, (int, float)) and div > 0:
        if div >= 3:
            score += 5
            signals.append(f"Good dividend yield: {div}%")
        elif div >= 1:
            score += 3
            signals.append(f"Decent dividend yield: {div}%")
        else:
            score += 1
            signals.append(f"Low dividend yield: {div}%")
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Quality tier
    if score >= 80:
        tier = "EXCELLENT"
    elif score >= 65:
        tier = "GOOD"
    elif score >= 50:
        tier = "AVERAGE"
    elif score >= 35:
        tier = "BELOW AVERAGE"
    else:
        tier = "POOR"
    
    return {
        "symbol": symbol.upper(),
        "score": score,
        "tier": tier,
        "signals": signals,
        "risks": risks,
        "ratios": {
            "pe": ratios.get("pe"),
            "pb": ratios.get("pb"),
            "debt_to_equity": ratios.get("debt_to_equity"),
            "roe": ratios.get("roe"),
            "roce": ratios.get("roce"),
            "profit_margin": ratios.get("profit_margin"),
            "dividend_yield": ratios.get("dividend_yield"),
        }
    }
