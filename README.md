# 📊 StockForge — Indian Stock Market Intelligence

> **Your complete investing and trading toolkit for the Indian stock market.**
> Daily analysis, screening, risk management, and actionable recommendations — all in one place.

---

## 🎯 Philosophy: Investing > Trading

StockForge is built for **long-term wealth creation**, not speculation. The system combines:

- **Fundamental analysis** — quality businesses with strong promoters, growing earnings, and reasonable valuations
- **Technical timing** — buy quality stocks at good entry points using RSI, MACD, Bollinger Bands, and moving averages
- **Risk management** — never risk more than 2% of capital on a single position; always use stop-losses
- **Scenario planning** — Bull/Base/Bear outcomes with probability-weighted expected returns

### Core Principle
**Buy great companies at fair prices. Hold through volatility. Add on dips. Exit when the thesis breaks.**

---

## 🚀 Quick Start

### Prerequisites
```bash
# System Python 3.12 (required — not Hermes venv)
python3.12 --version

# Install dependencies
/usr/bin/python3.12 -m pip install --break-system-packages yfinance pandas numpy requests beautifulsoup4 lxml
```

### Clone & Setup
```bash
# Already installed at /root/StockForge
cd /root/StockForge
chmod +x scripts/*.py
```

### MCP Servers (for Hermes Agent)
Already configured in `~/.hermes/config.yaml`:

| MCP Server | Tools | Status |
|---|---|---|
| **finstack-mcp** | 58 tools (NSE/BSE quotes, FII/DII, insider trading, fundamentals, options) | ✅ Active |
| **agentmemory** | Session memory | ✅ Active |
| **tapetide-mcp** | 26 tools (analyst ratings, estimates, screener, heatmaps) | 📝 Commented (needs token) |
| **groww-mcp** | Portfolio, orders, live quotes (requires Groww API token) | 📝 Pending |

---

## 📖 How to Use StockForge

### Daily Routine (Before Market Opens — 9:00 AM IST)

```bash
# 1. Get daily market intelligence briefing
python3 scripts/daily_intelligence.py

# Output: /root/StockForge/output/daily_briefing_YYYY-MM-DD.txt
# Includes: market overview, VIX, FII/DII, top movers, screens, recommendations
```

### Analyze a Single Stock

```bash
python3 scripts/analyze_stock.py RELIANCE
python3 scripts/analyze_stock.py TCS --full
```

**What you get:**
- Current price, change%, technical indicators (RSI, MACD, Bollinger, SMA, ATR)
- Fundamental score (0-100) with promoter holding, ROCE, ROE, debt analysis
- DCF valuation with upside/downside percentage
- **Investment Hypothesis** section covering:
  - 📰 News sentiment
  - 🏢 Company internals (promoter, FII/DII, pledge)
  - 📊 Technical setup
  - 📋 Fundamental quality
  - 💰 Valuation verdict
  - 🔮 12-month scenario (Bull/Base/Bear)
  - 🚀 Catalysts
  - ⚠️ Risks
- Risk management (position sizing, stop-loss, trailing stop)

### Stock Screening

```bash
# Run all screeners
python3 scripts/screen_stocks.py

# Screen Nifty 50 for fundamentally strong stocks
python3 scripts/screen_stocks.py --type fundamental --universe nifty50

# Screen for VCP (Volatility Contraction Pattern) setups
python3 scripts/screen_stocks.py --type vcp --universe nifty200

# Screen for breakout candidates
python3 scripts/screen_stocks.py --type breakout --universe nifty500
```

### Portfolio Tracking

```python
# Edit config/portfolio.json with your holdings
{
  "holdings": [
    {"symbol": "RELIANCE", "quantity": 10, "avg_price": 1250},
    {"symbol": "TCS", "quantity": 5, "avg_price": 3800}
  ],
  "cash": 200000
}
```

---

## 🧠 When to Use Each Screen

### 1. Fundamental Screen → Long-Term Investing (6+ months)
**Use when:** Building core portfolio positions
**Filters:** ROCE > 15%, Debt/Equity < 0.5, ROE > 15%, Revenue growth > 10%
**Verdict:** BUY/ACCUMULATE = quality business at fair price

### 2. VCP Screen → Swing Trading (2-8 weeks)
**Use when:** Looking for stocks about to breakout from consolidation
**Based on:** Mark Minervini's Volatility Contraction Pattern
**Filters:** Uptrend established, 2+ contractions, volume dry-up, near pivot
**Verdict:** BUY on breakout above pivot with volume

### 3. Breakout Screen → Momentum Trading (1-4 weeks)
**Use when:** Riding momentum in trending stocks
**Filters:** Price above 50-DMA & 200-DMA, volume spike, recent high
**Verdict:** BUY with tight stop-loss, trail aggressively

---

## 💰 Investing Strategy for Maximum Returns

### The Core-Satellite Approach

#### Core Portfolio (70% of capital) — Buy & Hold
**Goal:** 15-18% annual returns, compounding over 5-10 years

**Selection Criteria:**
1. **ROCE > 20%** — company generates strong returns on capital
2. **Revenue growth > 12% CAGR** (3-year average)
3. **Profit margin stable or expanding** — pricing power
4. **Debt/Equity < 0.5** — financially conservative
5. **Promoter holding > 40%** — skin in the game
6. **Promoter pledge = 0%** — no red flag
7. **FII + DII > 20%** — institutional confidence

**How many stocks:** 8-12 positions
**Position sizing:** 8-12% of portfolio each
**Rebalancing:** Quarterly — trim winners > 15% of portfolio, add to underweights

**Entry Strategy:**
- Use the Fundamental Screen to find quality stocks
- Check the Technical Screen for oversold conditions (RSI < 35)
- Buy in 2-3 tranches (don't go all-in at once)
- Set stop-loss at 2x ATR below entry

**Exit Strategy:**
- Sell when: ROCE drops below 15% for 2 consecutive quarters
- Sell when: Promoter starts pledging shares
- Sell when: Stock becomes overvalued (PE > 80 for non-growth, > 120 for growth)
- **Never sell because of market noise** — only sell when the thesis breaks

#### Satellite Portfolio (20% of capital) — Tactical Positions
**Goal:** 25-40% returns on swing trades and momentum plays

**Use VCP and Breakout screens:**
- Enter on confirmed breakouts with volume
- Set stop-loss at 5-8% below entry
- Trail stops using ATR method
- Take partial profits at 1:3 R:R (lock in gains, let rest run)

**Rules:**
- Max 3-4 satellite positions at a time
- Never average down on satellite positions
- If stop-loss hits, exit immediately — no exceptions

#### Cash Reserve (10% of capital) — Dry Powder
**Purpose:**
- Buy market dips (NIFTY -5% or more)
- Emergency liquidity
- New opportunity fund

**Deploy when:**
- VIX > 25 (fear = opportunity)
- Quality stocks become oversold (RSI < 30)
- Market correction of 10%+ — deploy in 3 tranches

---

## 📊 The Hypothesis Framework

Every StockForge recommendation includes a **Hypothesis** section (inspired by ContentForge's intelligence pipeline). This forces you to articulate WHY you're making the investment before committing capital.

### Hypothesis Structure

```
🧠 INVESTMENT HYPOTHESIS

📰 NEWS SENTIMENT:
  Positive/negative/neutral news flow and sentiment score

🏢 COMPANY INTERNALS:
  Promoter holding, pledge status, FII/DII ownership trends

📊 TECHNICAL:
  RSI, MACD, moving averages, support/resistance levels

📋 FUNDAMENTAL:
  ROCE, ROE, debt, margins, revenue growth score

💰 VALUATION:
  DCF intrinsic value, PE/PB comparison, upside/downside %

🔮 12-MONTH SCENARIO:
  Bull case (25% prob), Base case (50%), Bear case (25%)
  Probability-weighted expected return

🚀 CATALYSTS:
  What could drive the stock higher? (new products, policy changes, etc.)

⚠️ RISKS:
  What could go wrong? (regulatory, competition, macro, execution)
```

### How to Use the Hypothesis

1. **Before buying:** Read the full hypothesis. If you can't articulate the Bull case in 1 sentence, don't buy.
2. **After buying:** Re-read quarterly. If the thesis has changed (e.g., promoter started pledging, ROCE dropped), reconsider.
3. **When selling:** Check if the risks materialized or if the thesis is still intact.

---

## 🛡️ Risk Management Rules

### The 2% Rule
**Never risk more than 2% of your total capital on a single trade.**

Example: ₹10,00,000 portfolio → Max risk per trade = ₹20,000

If your stop-loss is 5% below entry:
- Max position = ₹20,000 / 0.05 = ₹4,00,000 (40% of portfolio)
- But cap at 25% per position → 16 shares instead

### Position Sizing Methods

| Method | When to Use | Formula |
|---|---|---|
| Fixed Fractional | Default | Risk = 2% of account |
| ATR-Based | Volatile stocks | Stop = 2x ATR below entry |
| Kelly Criterion | When you have edge data | f* = (bp - q) / b |

### Stop-Loss Placement

| Method | Best For | Formula |
|---|---|---|
| Structure-based | Swing trades | Below support - 1% buffer |
| ATR-based | All trades | Entry - (2x ATR) |
| Moving average | Trend following | Below 200-DMA - 1% |
| Percentage | Investing | 5-8% below entry |

### Trailing Stops (For Winners)

Once a position is up 15%+:
- Move stop-loss to break-even
- Trail at 2x ATR below highest price
- Or use 8% trailing stop for swing trades
- For long-term holds: trail below 200-DMA

---

## 📅 Money-Making Framework

### Daily (Mon-Fri, 6:30 AM IST)
- Run `daily_intelligence.py` → get market briefing
- Check for new BUY/ACCUMULATE signals
- Review existing holdings for stop-loss hits

### Weekly (Sunday)
- Review portfolio allocation (% per stock)
- Check if any positions exceeded 15% — trim if needed
- Screen for new opportunities
- Update watchlist

### Monthly
- Run full fundamental screen on NIFTY 200
- Check FII/DII flow trends
- Review and update thesis for each holding
- Rebalance if allocations drifted > 5%

### Quarterly
- Full portfolio review
- Check concall transcripts for growth triggers
- Update DCF valuations with latest earnings
- Consider tax-loss harvesting (March for FY end)

### Annually
- Calculate actual returns vs NIFTY 50
- Review strategy effectiveness
- Update screener filters based on market conditions
- Set next year's return target

---

## 📁 Project Structure

```
StockForge/
├── data/                    # Data fetching modules
│   ├── market_data.py       # yfinance quotes, history, indices
│   ├── fundamentals.py      # Screener.in financial data
│   ├── fii_dii.py           # FII/DII flow tracking
│   ├── news.py              # MoneyControl + LiveMint news
│   └── macro.py             # VIX, RBI rates, GSec yields
├── analysis/                # Analysis engines
│   ├── technical.py         # RSI, MACD, Bollinger, SMA, ATR
│   ├── fundamental.py       # 100-point fundamental scoring
│   └── valuation.py         # DCF + PE/PB benchmarking
├── screeners/               # Stock screeners
│   └── __init__.py          # Fundamental, VCP, breakout
├── intelligence/            # Intelligence & recommendations
│   ├── recommendation_engine.py  # Full hypothesis recommendations
│   ├── daily_briefing.py    # Daily market briefing
│   ├── stock_report.py      # Single stock report
│   ├── concalls/            # Concall transcript analysis
│   ├── scenarios/           # Bull/Base/Bear scenarios
│   ├── options/             # Black-Scholes + strategy builder
│   ├── breadth/             # Market health score
│   └── backtest/            # Backtest validator
├── risk/                    # Risk management
│   └── __init__.py          # Position sizing, stop-loss, trailing
├── portfolio/               # Portfolio tracking
│   └── portfolio.py         # Holdings, P&L, allocation
├── scripts/                 # CLI entry points
│   ├── daily_intelligence.py
│   ├── analyze_stock.py
│   └── screen_stocks.py
├── config/                  # Configuration files
│   ├── watchlist.txt        # 30 NIFTY 50 stocks
│   ├── portfolio.json       # Your holdings
│   └── screener_filters.json
└── output/                  # Generated reports
    └── daily_briefing_*.txt
```

---

## 🔧 Integrated Tools & Data Sources

| Tool | Purpose | Cost |
|---|---|---|
| **yfinance** | NSE/BSE historical data, quotes | Free |
| **finstack-mcp** | 58 tools: real-time NSE/BSE, FII/DII, insider trading, credit ratings, BRSR/ESG | Free |
| **screener.in** | Fundamentals, concall transcripts, shareholding | Free |
| **MoneyControl/LiveMint** | News and sentiment | Free |
| **tapetide-mcp** | Analyst ratings, estimates, screeners (optional) | Free tier |
| **groww-mcp** | Live portfolio, orders (optional) | Free with Groww account |

---

## ⚠️ Important Limitations

1. **TPIN for Selling:** Selling DEMAT holdings requires manual TPIN via Groww app — cannot be automated
2. **Market Hours:** Orders only during 9:15 AM - 3:30 PM IST (AMO supported for next day)
3. **Data Delay:** yfinance data is 15-min delayed during market hours
4. **Not Financial Advice:** All analysis is for educational purposes — do your own research

---

## 🤖 Hermes Integration

StockForge is integrated with Hermes Agent via:

1. **MCP Servers:** finstack-mcp provides 58 tools accessible to the AI agent
2. **Skill:** `~/.hermes/skills/stockforge/SKILL.md` — tells Hermes how to use StockForge
3. **Cron:** Daily intelligence briefing at 6:30 AM IST (Mon-Fri)
4. **Telegram:** Briefings delivered directly to your chat

### Useful Hermes Commands
```
"Run StockForge daily intelligence"
"Analyze RELIANCE with full hypothesis"
"Screen Nifty 50 for fundamentally strong stocks"
"What's the market breadth today?"
"Show me my portfolio P&L"
"Calculate position size for TCS with ₹10L account"
```

---

## 📞 Credits & Attribution

StockForge integrates concepts and patterns from:

- **Bhala-Srinivash/nse-trading-skills** — Position sizing, stop-loss, trailing stops, RSI divergence
- **samyakjain0606/awesome-stock-skills** — Concall analysis, growth trigger extraction, variant perception
- **ajeeshworkspace/indian-trading-skills** — VCP screener, scenario analysis, options strategies, market breadth
- **finstacklabs/finstack-mcp** — 58-tool MCP server for Indian markets
- **Tapetide-hq/tapetide-stock-research-mcp** — Analyst ratings and estimates

All adapted and integrated into a unified Python-based system for the Indian market.

---

*Built for Kishore (@devopsbyte) — Infra Eng Lead, long-term investor.*
*Disclaimer: For informational purposes only. Not investment advice.*
