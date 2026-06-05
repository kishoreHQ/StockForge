# StockForge -- Full Setup Guide

This is the **complete, step-by-step** setup walkthrough. If you are an AI coding agent, prefer `AGENTS.md` (it is the agent-optimized entry point). This document is more verbose and human-friendly.

## 0. Prerequisites

- **Python 3.10+** on your PATH (`python3 --version`)
- **git**
- **pip** (or `uv` -- either works)
- **Internet access** (for `yfinance` and NewsAPI)
- ~100 MB free disk

Optional:
- A free [NewsAPI](https://newsapi.org/register) key for sentiment analysis
- An [Angel One](https://www.angelone.in/) account for real-time NSE quotes

Tested on: Ubuntu 22.04, macOS 14, Windows 11 WSL2.

## 1. Clone the repo

```bash
git clone https://github.com/kishoreHQ/StockForge.git
cd StockForge
```

## 2. Run setup

```bash
make setup
# or, if you prefer the raw script:
./setup.sh
```

What this does, in order:

1. **Picks a Python interpreter.** In priority order:
   - Local `.venv/bin/python` if it exists
   - `$STOCKFORGE_PYTHON` env var if set and executable
   - `python3` on PATH
2. **Creates a venv** at `.venv/` if one doesn't exist and the active Python is the system one.
3. **Installs dependencies** from `requirements.txt` into the venv (or with `--break-system-packages` if using system Python).
4. **Verifies imports** -- confirms `yfinance`, `pandas`, `aynse` (optional) all import.
5. **Creates output directories** at `output/`, `output/briefings/`, `output/reports/`, `output/portfolio/`.

Expected output ends with:
```
✅ StockForge setup complete!
```

## 3. (Optional) Configure API keys

```bash
cp .env.example .env
nano .env
```

Set the keys you have. The repo works without any keys -- it falls back to public yfinance data.

```dotenv
# Free tier: 100 requests/day, register at https://newsapi.org/register
NEWSAPI_KEY=your_newsapi_key_here

# Real-time NSE quotes (optional)
ANGEL_ONE_API_KEY=your_angel_one_key
ANGEL_ONE_APP_KEY=your_app_key
ANGEL_ONE_USER_ID=your_user_id

# Custom watchlist (defaults to config/watchlist.txt)
WATCHLIST_FILE=config/watchlist.txt
```

`.env` is in `.gitignore` and will not be committed.

## 4. Verify the install

```bash
make verify
```

Expected: `34 passed` in `<1 second`. This runs `tests/test_portability.py`, which checks:

- All 8 scripts exist and parse
- All helper modules exist (`analysis/`, `intelligence/`, `screeners/`, `portfolio/`, `risk/`)
- No hardcoded user paths anywhere
- `config/watchlist.txt` and `config/screener_filters.json` exist
- `Makefile`, `AGENTS.md`, `SETUP.md`, `.env.example`, `requirements.txt`, `README.md` exist
- Makefile has `help:`, `setup:`, `verify:` targets

If anything fails, the error message names the missing file or offending line.

## 5. Run your first analysis

```bash
# Top 10 growth picks for today
make daily

# Brief on a single stock
make analyze STOCK=TCS

# Read the markdown report
ls output/
cat output/picks_$(date +%Y-%m-%d).md
```

## 6. Schedule recurring runs (optional)

The repo does not include cron files -- add them to your system crontab:

```bash
crontab -e
```

Append:

```cron
# Mon-Fri 7:00 AM IST = 01:30 UTC: top-10 picks
30 1 * * 1-5 cd /path/to/StockForge && .venv/bin/python scripts/daily_top_picks.py >> output/cron.log 2>&1

# Mon-Fri 7:30 AM IST = 02:00 UTC: daily briefing
0 2 * * 1-5 cd /path/to/StockForge && .venv/bin/python scripts/daily_intelligence.py >> output/cron.log 2>&1
```

Replace `/path/to/StockForge` with the real install path.

## Common issues

### `ModuleNotFoundError: No module named 'yfinance'`

You skipped `make setup` (or your venv isn't activated). Run:

```bash
make setup
# or manually:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### `Permission denied` running `setup.sh`

```bash
chmod +x setup.sh
```

### `make: command not found`

Install make. On Debian/Ubuntu: `sudo apt install make`. On macOS: `xcode-select --install`.

### `yfinance` returns empty data

Yahoo Finance is rate-limiting or your network blocks it. The repo will print a warning and skip that symbol. Try again in 5-10 minutes.

### NewsAPI returns 401

Your `NEWSAPI_KEY` in `.env` is invalid or missing. The script will fall back to no-sentiment mode and continue.

### `aynse` fails to import

`aynse` is **optional**. The repo tries to import it; if it fails, sentiment falls back to news-only. To silence the warning, `pip install aynse` (note: as of 2026, aynse is not always on PyPI -- check the [project](https://pypi.org/project/aynse/)).

## What gets written where

| Path | Created by | Content |
|------|------------|---------|
| `output/picks_YYYY-MM-DD.json` | `scripts/daily_top_picks.py` | Top 10 picks (machine-readable) |
| `output/picks_YYYY-MM-DD.md` | same | Same, in markdown (Telegram-friendly) |
| `output/briefings/daily_briefing_YYYY-MM-DD.txt` | `scripts/daily_intelligence.py` | Plain-text briefing |
| `output/reports/{SYMBOL}_YYYY-MM-DD.md` | `scripts/analyze_stock.py` | Per-stock analysis |
| `output/portfolio/portfolio.json` | `scripts/llm_portfolio.py` | Paper-trade state (auto-updated) |
| `output/cron.log` | cron | Stdout/stderr from scheduled runs |

The `output/` directory is gitignored -- generated reports stay local.

## Verifying the agent-clonability promise

From a brand-new machine:

```bash
git clone https://github.com/kishoreHQ/StockForge.git
cd StockForge
make setup
make verify
make daily
```

If all three commands succeed and you have a `output/picks_*.md` file, the repo is fully working end-to-end with no prior context.

## Next steps

- Read `README.md` for the user-facing feature docs (what each script does, what each output means)
- Read `AGENTS.md` for the agent-optimized command reference
- Add cron entries (step 6) to fully automate
- Configure `.env` with NewsAPI / Angel One keys for richer data
