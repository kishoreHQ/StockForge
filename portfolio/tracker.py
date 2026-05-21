"""StockForge Portfolio - Track holdings and P&L."""
import json
import os
from data.market_data import get_batch_quotes
from datetime import datetime


DEFAULT_PORTFOLIO = {
    "holdings": [
        {"symbol": "RELIANCE", "quantity": 10, "avg_price": 2450, "buy_date": "2025-01-15"},
        {"symbol": "TCS", "quantity": 5, "avg_price": 3800, "buy_date": "2025-03-20"},
        {"symbol": "HDFCBANK", "quantity": 20, "avg_price": 1600, "buy_date": "2025-02-10"},
    ],
    "cash": 50000,
    "updated": datetime.now().strftime("%Y-%m-%d"),
}

PORTFOLIO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "config", "portfolio.json")


def load_portfolio() -> dict:
    """Load portfolio from config file."""
    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            return json.load(f)
    return DEFAULT_PORTFOLIO.copy()


def save_portfolio(portfolio: dict):
    """Save portfolio to config file."""
    os.makedirs(os.path.dirname(PORTFOLIO_PATH), exist_ok=True)
    portfolio["updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(portfolio, f, indent=2)


def get_portfolio_summary() -> str:
    """Get current portfolio summary with P&L."""
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    cash = portfolio.get("cash", 0)
    
    if not holdings:
        return "📂 Portfolio is empty. Add holdings to track."
    
    lines = []
    lines.append("=" * 60)
    lines.append("📂 PORTFOLIO SUMMARY")
    lines.append(f"   {portfolio.get('updated', 'N/A')}")
    lines.append("=" * 60)
    lines.append("")
    
    symbols = [h["symbol"] for h in holdings]
    quotes = get_batch_quotes(symbols)
    quote_map = {q["symbol"]: q for q in quotes}
    
    total_invested = 0
    total_current = 0
    total_pnl = 0
    
    lines.append(f"  {'Symbol':<15} {'Qty':>5} {'Avg':>10} {'LTP':>10} {'Invested':>12} {'Current':>12} {'P&L':>12} {'P&L%':>7}")
    lines.append("  " + "-" * 85)
    
    for h in holdings:
        sym = h["symbol"]
        qty = h["quantity"]
        avg = h["avg_price"]
        invested = qty * avg
        
        q = quote_map.get(sym, {})
        ltp = q.get("price", avg)
        current = qty * ltp
        pnl = current - invested
        pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
        
        total_invested += invested
        total_current += current
        total_pnl += pnl
        
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        
        lines.append(f"  {sym:<15} {qty:>5} {avg:>10.2f} {ltp:>10.2f} "
                    f"{invested:>12,.0f} {current:>12,.0f} "
                    f"{pnl_icon}{pnl:>+11,.0f} {pnl_pct:>+6.1f}%")
    
    lines.append("  " + "-" * 85)
    total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested > 0 else 0
    lines.append(f"  {'TOTAL':<15} {'':>5} {'':>10} {'':>10} "
                f"{total_invested:>12,.0f} {total_current:>12,.0f} "
                f"{total_pnl:>+12,.0f} {total_pnl_pct:>+6.1f}%")
    lines.append(f"  Cash: ₹{cash:,.0f}")
    lines.append(f"  Total Portfolio Value: ₹{total_current + cash:,.0f}")
    lines.append("")
    
    # Allocation
    if total_current > 0:
        lines.append("  📊 ALLOCATION:")
        for h in holdings:
            sym = h["symbol"]
            q = quote_map.get(sym, {})
            ltp = q.get("price", h["avg_price"])
            current = h["quantity"] * ltp
            alloc = (current / total_current) * 100
            lines.append(f"     {sym:<15} {alloc:>5.1f}%")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)
