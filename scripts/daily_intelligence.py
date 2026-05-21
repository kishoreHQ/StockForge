#!/usr/bin/python3.12
"""StockForge Daily Intelligence - Main entry point for cron jobs."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.daily_briefing import generate_daily_briefing, save_briefing


def main():
    print("🚀 Generating daily stock intelligence briefing...")
    print()
    
    briefing = generate_daily_briefing()
    print(briefing)
    print()
    
    filepath = save_briefing(briefing)
    print(f"💾 Briefing saved to: {filepath}")
    
    return briefing


if __name__ == "__main__":
    main()
