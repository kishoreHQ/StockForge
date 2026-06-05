# StockForge -- AGENTS.md

> **Read this first if you are an AI coding agent (Cursor, Copilot, Claude Code, Codex, OpenCode, Gemini, Qwen, etc.).** A human can also follow it, but it's written for agents.

## What this repo is

**StockForge** is an Indian stock-market intelligence pipeline. It produces:

- **Daily top-10 growth picks** across NIFTY 200, scored with a multi-factor engine (confidence + alpha-zoo + dynamic TP/SL)
- **Per-stock analysis reports** (technical + fundamental + sentiment)
- **Daily briefings** pushed to Telegram
- **Portfolio tracker** with paper-trade support
- **Risk reports** for individual holdings

It runs as a collection of standalone Python scripts. There is **no web server, no API, no database** -- just scripts that read CSVs / call public APIs and write markdown / JSON / TXT reports to `output/`.

## Quickstart (for any agent)

```bash
# 1. Clone
git clone https://github.com/kishoreHQ/StockForge.git
cd StockForge

# 2. Set up
make setup                  # creates .venv, installs requirements

# 3. Run
make help                   # see all targets
make daily                  # daily top-10 picks (writes output/picks_*.json + .md)
make analyze STOCK=RELIANCE # deep-dive on a single stock
make verify                 # portability + sanity checks
```

That's it. Optional: copy `.env.example` to `.env` and add `NEWSAPI_KEY` for sentiment.

## Repo structure

```
.
|-- AGENTS.md                <-- you are here
|-- SETUP.md                 <-- full setup walkthrough
|-- README.md                <-- original user-facing documentation
|-- Makefile                 <-- canonical command surface
|-- setup.sh                 <-- legacy shell setup (now portable, .venv-aware)
|-- push.sh                  <-- legacy auto-push helper
|-- requirements.txt         <-- Python dependencies
|-- .env.example             <-- optional API keys template
|-- .gitignore
|
|-- analysis/                <-- stock analysis library
|   |-- llm_agent.py
|   `-- sentiment.py
|
|-- intelligence/            <-- daily recommendation engines
|   |-- daily_briefing.py
|   |-- stock_report.py
|   `-- recommendation_engine.py
|
|-- screeners/               <-- universe filters (fundamental, technical)
|   `-- __init__.py
|
|-- portfolio/               <-- paper-trade tracker
|   `-- tracker.py
|
|-- risk/                    <-- risk reports
|
|-- scripts/                 <-- executable entry points
|   |-- daily_intelligence.py
|   |-- daily_top_picks.py
|   |-- analyze_stock.py
|   |-- screen_stocks.py
|   |-- llm_portfolio.py
|   |-- stock_pulse.py
|   |-- stock_risk_report.py
|   `-- test_alpha_zoo.py
|
|-- config/
|   |-- watchlist.txt        <-- 30 NIFTY 50 symbols (overridable via env)
|   |-- screener_filters.json
|   `-- portfolio.json       <-- paper-trade state (gitignored)
|
|-- output/                  <-- all generated reports (gitignored)
|   |-- picks_YYYY-MM-DD.md
|   |-- briefings/
|   |-- reports/
|   `-- portfolio/
|
`-- tests/
    `-- test_portability.py  <-- 34 checks: cloneable + importable
```

## Configuration

| Env var | Required? | Default | Purpose |
|---------|-----------|---------|---------|
| `STOCKFORGE_PYTHON` | no | `python3` on PATH | Override the Python interpreter used by `setup.sh` and Makefile |
| `WATCHLIST_FILE` | no | `config/watchlist.txt` | Path to a custom watchlist file |
| `NEWSAPI_KEY` | no | (none) | NewsAPI.org key for sentiment analysis. Free tier: 100 req/day. |
| `ANGEL_ONE_API_KEY` / `_APP_KEY` / `_USER_ID` | no | (none) | Angel One real-time quotes. Optional. |

The repo **does not** require any API key to function. Daily top-10 picks use public yfinance data.

## Commands (Makefile targets)

| Target | What it does |
|--------|--------------|
| `make help` | Print all available targets |
| `make setup` | Create venv, install requirements, make output dirs |
| `make install` | Same as `setup` |
| `make verify` | Run pytest + script smoke tests (no network) |
| `make daily` | Run `scripts/daily_top_picks.py` -- produces top-10 picks |
| `make brief` | Run `scripts/daily_intelligence.py` -- produce daily briefing |
| `make analyze STOCK=RELIANCE` | Run `scripts/analyze_stock.py RELIANCE` |
| `make screen TYPE=fundamental` | Run `scripts/screen_stocks.py --type fundamental` |
| `make risk` | Run `scripts/stock_risk_report.py` |
| `make pulse` | Run `scripts/stock_pulse.py` (news + sentiment) |
| `make clean` | Remove `output/` and `__pycache__/` |
| `make lint` | Compile-check all Python (no execution) |

## Schedule (cron)

The repo does **not** include cron files. A typical crontab entry is:

```cron
# Daily top-10 picks at 7 AM IST Mon-Fri (Mon-Fri 01:30 UTC)
30 1 * * 1-5  cd /path/to/StockForge && .venv/bin/python scripts/daily_top_picks.py >> output/cron.log 2>&1

# Daily briefing at 7:30 AM IST
30 2 * * 1-5  cd /path/to/StockForge && .venv/bin/python scripts/daily_intelligence.py >> output/cron.log 2>&1
```

The repo is designed to be run from any directory -- every script uses `__file__` to locate its dependencies, never absolute paths.

## Dependencies

| Package | Version | Used for |
|---------|---------|----------|
| `yfinance` | >=0.2.40 | OHLCV + fundamentals (free, no key) |
| `aynse` | >=2.0.0 | NSE-specific helpers (optional) |
| `pandas` | >=2.0.0 | Dataframes |
| `numpy` | >=1.24.0 | Numeric ops |
| `requests` | >=2.28.0 | HTTP for NewsAPI |
| `beautifulsoup4` | >=4.12.0 | HTML parsing for screener.in |
| `lxml` | >=4.9.0 | XML/HTML back-end |
| `pytest` | (dev) | Test runner |

System: Python 3.10+. Linux / macOS / WSL all supported.

## How the daily picks work

1. `daily_top_picks.py` reads the watchlist (`config/watchlist.txt`, default: 30 NIFTY 50 symbols)
2. For each symbol it fetches the last 6 months of OHLCV via yfinance
3. It computes 10+ alpha-zoo factors (momentum, mean-reversion, volatility, ROC, etc.)
4. It runs the **ConfidenceScorer** (port from FinceptTerminal) to weight the factors
5. It runs the **DynamicTPSL** engine to set target prices and stop-losses
6. It returns the top 10 by composite score, sorted by confidence x alpha-zoo
7. Output: `output/picks_YYYY-MM-DD.json` and `output/picks_YYYY-MM-DD.md`

The 6 historical "swarm" factors (Buffett, Graham, Lynch, etc.) live in `intelligence/recommendation_engine.py` and are scored separately.

## What "agent-cloneable" means here

After `git clone`, an agent should be able to:

1. `make setup` -> venv created, deps installed, output dirs made
2. `make verify` -> 34 tests pass (all 8 scripts import, no hardcoded paths, all helper modules present, all config files exist)
3. `make daily` -> produces `output/picks_2026-XX-XX.md` with top-10

If any of those fail, the repo is broken. The `tests/test_portability.py` file enforces this.

## Troubleshooting

- **`ModuleNotFoundError: yfinance`** -> run `make setup`
- **`Permission denied` on `setup.sh`** -> `chmod +x setup.sh` (only needed if you cloned via HTTP and lost the bit)
- **No picks produced** -> yfinance rate-limited you. Wait 5 min, try again. Or add `WATCHLIST_FILE=config/watchlist.txt` to limit the universe.
- **NewsAPI 429** -> out of daily quota (free tier = 100/day). Wait until midnight UTC.
- **`aynse` fails to import** -> it's optional. Sentiment still works without it.

## Related repos (same family)

- `career-ops` -- AI job-search pipeline
- `aicreator` -- AI influencer content factory (Telegram, IG)
- `mission-control` -- unified web dashboard for all of the above

## License

Personal project. See `LICENSE` if present, otherwise treat as "all rights reserved".
