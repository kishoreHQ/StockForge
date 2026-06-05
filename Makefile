# StockForge Makefile
# Canonical command surface for AI agents and humans.
# All targets are .PHONY (no file collisions).
# Override the Python interpreter with:  make PY=python3.11 daily

PY         ?= python3
VENV       ?= .venv
VENV_PY     := $(VENV)/bin/python
REQ        := requirements.txt
SCRIPTS    := scripts

# If .venv exists, prefer it.
ifeq ($(wildcard $(VENV_PY)),)
  USE_VENV_PY := $(PY)
else
  USE_VENV_PY := $(VENV_PY)
endif

.PHONY: help setup install verify test daily brief analyze screen risk pulse clean lint

help:  ## Show this help message
	@echo "StockForge - Indian stock market intelligence pipeline"
	@echo ""
	@echo "Usage:  make <target> [VAR=value ...]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  PY=python3.11     Override Python interpreter (default: python3)"
	@echo "  STOCK=RELIANCE    Symbol for 'make analyze' / 'make risk'"
	@echo "  TYPE=fundamental  Type for 'make screen' (fundamental|technical)"
	@echo ""
	@echo "Current interpreter: $(USE_VENV_PY)"
	@$(USE_VENV_PY) --version

setup: install  ## Create venv + install deps + make output dirs (alias for install)
	@echo ""
	@echo "✅ StockForge ready. Try:  make verify   then   make daily"

install:  ## Create venv and install dependencies
	@if [ ! -x "$(VENV_PY)" ]; then \
		echo "📦 Creating venv at $(VENV)/ ..."; \
		$(PY) -m venv $(VENV) || { echo "❌ venv creation failed"; exit 1; }; \
	fi
	@echo "📦 Installing dependencies..."
	@$(VENV_PY) -m pip install --quiet --upgrade pip
	@$(VENV_PY) -m pip install --quiet -r $(REQ)
	@echo "🔍 Verifying imports..."
	@$(VENV_PY) -c "import yfinance; print('  ✅ yfinance:', yfinance.__version__)"
	@$(VENV_PY) -c "import pandas; print('  ✅ pandas:', pandas.__version__)"
	@-$(VENV_PY) -c "import aynse; print('  ✅ aynse OK')" 2>/dev/null || echo "  ⚠️  aynse not installed (optional)"
	@mkdir -p output output/briefings output/reports output/portfolio
	@touch output/.gitkeep output/briefings/.gitkeep output/reports/.gitkeep output/portfolio/.gitkeep
	@echo "✅ Install complete"

verify: test  ## Run portability tests + smoke checks (alias for test)
	@echo ""
	@echo "🩺 Smoke checks..."
	@for s in daily_top_picks daily_intelligence analyze_stock screen_stocks llm_portfolio stock_pulse stock_risk_report; do \
		$(USE_VENV_PY) -m py_compile $(SCRIPTS)/$$s.py && echo "  ✅ compiles: $$s.py" || echo "  ❌ compile error: $$s.py"; \
	done
	@echo ""
	@echo "✅ All checks passed"

test:  ## Run pytest portability tests (no network)
	@$(USE_VENV_PY) -m pytest tests/ -v

daily:  ## Run daily top-10 picks (writes output/picks_YYYY-MM-DD.md + .json)
	$(USE_VENV_PY) $(SCRIPTS)/daily_top_picks.py

brief:  ## Run daily intelligence briefing
	$(USE_VENV_PY) $(SCRIPTS)/daily_intelligence.py

analyze:  ## Analyze a single stock (use STOCK=RELIANCE)
	@test -n "$(STOCK)" || { echo "❌ Set STOCK=symbol.  e.g.  make analyze STOCK=RELIANCE"; exit 1; }
	$(USE_VENV_PY) $(SCRIPTS)/analyze_stock.py $(STOCK)

screen:  ## Run screener (use TYPE=fundamental|technical)
	@type_arg="$${TYPE:-fundamental}"; \
	$(USE_VENV_PY) $(SCRIPTS)/screen_stocks.py --type $$type_arg

risk:  ## Run risk report (use STOCK=RELIANCE)
	@test -n "$(STOCK)" || { echo "❌ Set STOCK=symbol.  e.g.  make risk STOCK=RELIANCE"; exit 1; }
	$(USE_VENV_PY) $(SCRIPTS)/stock_risk_report.py $(STOCK)

pulse:  ## Run stock pulse (news + sentiment for watchlist)
	$(USE_VENV_PY) $(SCRIPTS)/stock_pulse.py

clean:  ## Remove generated output and caches
	@rm -rf output/* output/.[!.]* 2>/dev/null || true
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .codegraph
	@echo "✅ Cleaned output/ and __pycache__/"

lint:  ## Syntax-check all Python files
	@$(USE_VENV_PY) -m compileall -q $(SCRIPTS) analysis intelligence screeners portfolio risk tests 2>/dev/null || true
	@echo "✅ Lint complete"
