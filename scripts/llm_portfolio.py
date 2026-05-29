"""
StockForge LLM Portfolio Agent — CLI Entry Point

Usage:
    # Prompt mode (prints analysis prompt for Hermes/LLM to reason)
    python3 scripts/llm_portfolio.py --tickers RELIANCE,TCS,HDFCBANK

    # Auto mode with specific model
    python3 scripts/llm_portfolio.py --tickers RELIANCE,TCS,HDFCBANK,INFY,ITC --mode auto --model gpt-4o-mini

    # Use Nifty 50 default universe
    python3 scripts/llm_portfolio.py --universe nifty50

    # Performance history
    python3 scripts/llm_portfolio.py --history
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.llm_agent import LLMStockAgent

NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "ITC", "KOTAKBANK", "LT", "SBIN", "BHARTIARTL",
    "AXISBANK", "HINDUNILVR", "BAJFINANCE", "TITAN", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "NESTLE", "WIPRO", "ULTRACEMCO",
    "POWERGRID", "NTPC", "ONGC", "COALINDIA", "BAJAJFINSV",
]


def main():
    parser = argparse.ArgumentParser(description="StockForge LLM Portfolio Agent")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., RELIANCE,TCS)")
    parser.add_argument("--universe", type=str, default="nifty50", choices=["nifty50", "nifty10"],
                        help="Pre-built universe (default: nifty50)")
    parser.add_argument("--mode", type=str, default="prompt", choices=["prompt", "auto"],
                        help="'prompt' to print analysis, 'auto' to call LLM")
    parser.add_argument("--model", type=str, default="deepseek-v4-pro",
                        help="LLM model name (auto mode only)")
    parser.add_argument("--history", action="store_true", help="Show performance history")
    parser.add_argument("--output", type=str, help="Save prompt to file")

    args = parser.parse_args()

    agent = LLMStockAgent("StockForge Portfolio Manager", model_name=args.model)

    # History mode
    if args.history:
        print(agent.get_performance_summary())
        return

    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif args.universe == "nifty10":
        tickers = NIFTY_50[:10]
    else:
        tickers = NIFTY_50[:5]  # default: top 5 for quick analysis

    print(f"📊 Analyzing {len(tickers)} stocks: {', '.join(tickers)}")
    print(f"🔄 Mode: {args.mode}")

    result = agent.analyze(tickers, mode=args.mode)

    if result.get("error"):
        print(f"❌ Error: {result['error']}")
        return

    formatted = agent.format_allocation(result)
    print(formatted)

    # Save prompt if requested
    if args.output and result.get("prompt"):
        with open(args.output, "w") as f:
            f.write(result["prompt"])
        print(f"\n💾 Prompt saved to: {args.output}")

    # Print alpha summary
    print("\n📊 Alpha Zoo Summary:")
    for ticker, alpha in result.get("alpha_scores", {}).items():
        agg = alpha.get("aggregate", "N/A")
        signal = alpha.get("signal", "N/A")
        themes = alpha.get("themes", {})
        top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
        theme_str = " | ".join(f"{t}: {s:.0f}" for t, s in top_themes) if top_themes else ""
        print(f"  {ticker:<12} {agg if isinstance(agg, (int, float)) else 'N/A':>5} {signal:<12} {theme_str}")


if __name__ == "__main__":
    main()
