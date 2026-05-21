#!/usr/bin/python3.12
"""StockForge - Screen stocks by type."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screeners import run_screen


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="StockForge Stock Screener")
    parser.add_argument("--type", choices=["fundamental", "vcp", "breakout", "all"],
                       default="fundamental", help="Screen type")
    parser.add_argument("--limit", type=int, default=10, help="Max results")
    parser.add_argument("--universe", choices=["nifty50", "next50", "nifty500"],
                       default="nifty50", help="Stock universe")
    parser.add_argument("--min-score", type=int, default=60,
                       help="Minimum fundamental score (for fundamental screen)")
    
    args = parser.parse_args()
    
    from data.market_data import get_index_constituents
    universe = get_index_constituents(args.universe)
    
    print(f"🔍 Running {args.type.upper()} screen on {args.universe.upper()} ({len(universe)} stocks)")
    print(f"   Limit: {args.limit}")
    print()
    
    results = run_screen(args.type, universe)
    
    if isinstance(results, dict):
        # All screens
        for screen_name, screen_results in results.items():
            print(f"\n{'=' * 50}")
            print(f"  {screen_name.upper()} SCREEN")
            print(f"{'=' * 50}")
            _print_screen_results(screen_name, screen_results[:args.limit])
    else:
        _print_screen_results(args.type, results[:args.limit])


def _print_screen_results(screen_type, results):
    if not results:
        print("  No stocks matched the screen criteria.")
        return
    
    print(f"  Found {len(results)} matches:\n")
    
    if screen_type == "fundamental":
        for r in results:
            print(f"  💎 {r['symbol']} - Score: {r['score']}/100 ({r['tier']})")
            print(f"     PE: {r.get('pe', 'N/A')}, ROCE: {r.get('roce', 'N/A')}%, "
                  f"ROE: {r.get('roe', 'N/A')}%, D/E: {r.get('debt_to_equity', 'N/A')}")
            for s in r.get("signals", [])[:2]:
                print(f"     ✅ {s}")
            print()
    
    elif screen_type == "vcp":
        for r in results:
            print(f"  📊 {r['symbol']} - VCP Score: {r['vcp_score']}/6")
            print(f"     Price: ₹{r['price']}, RSI: {r['rsi']}, "
                  f"Vol Ratio: {r['volume_ratio']}x")
            print(f"     vs 52W High: {r['vs_52w_high_pct']:.1f}%")
            print()
    
    elif screen_type == "breakout":
        for r in results:
            print(f"  🚀 {r['symbol']} - Near Breakout")
            print(f"     Price: ₹{r['price']}, Near 20D High: ₹{r['near_20d_high']} "
                  f"({r['distance_pct']:.1f}%)")
            print(f"     Volume: {r['volume_ratio']}x avg, RSI: {r['rsi']}")
            print(f"     Above MAs: {r['above_ma_count']}/3")
            print()


if __name__ == "__main__":
    main()
