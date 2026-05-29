"""
StockForge LLM Portfolio Agent

Wraps StockForge's existing analysis (alpha_zoo, technical, fundamental,
news) and produces LLM-driven portfolio allocations with reasoning.

Two modes:
  1. 'prompt' — returns the structured prompt string (for Hermes to reason about)
  2. 'auto'   — calls litellm directly (requires API key)

Inspired by LiveTradeBench's base_agent.py architecture.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Ensure StockForge path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import get_quote, get_history, nse_symbol
from data.news import get_moneycontrol_news, get_livemint_news
from analysis.alpha_zoo import score_all_alphas
from analysis.technical import calculate_rsi as _rsi, calculate_macd as _macd, calculate_bollinger_bands as _bb
from analysis.fundamental import score_fundamentals


# ── Alpha Zoo Scoring Helpers ──────────────────────────────────────────────

def _build_price_data(hist):
    """Convert yfinance history DataFrame to price_data dict for alpha_zoo."""
    if hist.empty:
        return {}
    close = hist["Close"].dropna()
    return {
        "close": close.tolist(),
        "open": hist["Open"].dropna().tolist(),
        "high": hist["High"].dropna().tolist(),
        "low": hist["Low"].dropna().tolist(),
        "volume": hist["Volume"].dropna().tolist(),
    }


def _safe_rsi(close_series, period=14):
    """Calculate RSI from a pandas Series (safe wrapper)."""
    try:
        from analysis.technical import calculate_rsi
        vals = calculate_rsi(close_series, period)
        return round(vals.iloc[-1], 1) if not vals.empty else None
    except Exception:
        return None


def _short_sma(hist, window):
    """Short SMA from history (handles empty)."""
    if hist.empty or len(hist) < window:
        return None
    return round(hist["Close"].iloc[-window:].mean(), 2)


# ── Agent ──────────────────────────────────────────────────────────────────

class LLMStockAgent:
    """LLM-powered portfolio manager for Indian stocks.

    Combines StockForge's analysis engines into a structured prompt
    that an LLM can reason about to produce portfolio allocations.

    Usage:
        agent = LLMStockAgent("Portfolio_Manager")
        result = agent.analyze(["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"])
        print(agent.format_allocation(result))
    """

    def __init__(self, name: str, model_name: str = "deepseek-v4-pro"):
        self.name = name
        self.model_name = model_name
        self.available = True
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self._last_price: Dict[str, float] = {}
        self.last_llm_input: Optional[Dict[str, Any]] = None
        self.last_llm_output: Optional[Dict[str, Any]] = None

        # Allocation tracking
        self.allocation_history: List[Dict[str, Any]] = []
        self.previous_allocations: Dict[str, float] = {}
        self.initial_cash = 100000.0
        self.cash_balance = 100000.0
        self.positions: Dict[str, Dict[str, Any]] = {}

    # ── Core Pipeline ──────────────────────────────────────────────────

    def analyze(self, tickers: List[str], date: Optional[str] = None,
                mode: str = "prompt") -> Dict[str, Any]:
        """Run full analysis pipeline on a set of tickers.

        Args:
            tickers: List of NSE symbols (e.g., ['RELIANCE', 'TCS'])
            date: Optional date string for backtesting
            mode: 'prompt' (returns prompt) or 'auto' (calls LLM)

        Returns:
            Dict with 'prompt' (str), 'allocations' (dict, if auto),
            'market_data', 'alpha_scores', etc.
        """
        print(f"\n{'='*60}")
        print(f"🤖 {self.name} — Analyzing {len(tickers)} stocks")
        print(f"{'='*60}")

        # 1. Fetch market data
        market_data = self._fetch_market_data(tickers)
        if not market_data:
            return {"error": "No market data fetched"}

        # 2. Fetch alpha zoo scores
        alpha_scores = self._fetch_alpha_scores(tickers)

        # 3. Fetch fundamentals
        fundamentals = self._fetch_fundamentals(tickers)

        # 4. Fetch news
        news_data = self._fetch_news_data(tickers)

        # 5. Build analysis sections
        market_analysis = self._prepare_market_analysis(market_data, alpha_scores)
        fundamental_analysis = self._prepare_fundamental_analysis(fundamentals)
        news_analysis = self._prepare_news_analysis(tickers, news_data)
        account_analysis = self._prepare_account_analysis()

        # 6. Combine into full prompt
        full_analysis = self._combine_analysis(
            market_analysis, fundamental_analysis, news_analysis, account_analysis
        )
        prompt = self._get_portfolio_prompt(full_analysis, tickers, date)

        # 7. Store for history
        self.last_llm_input = {
            "prompt": prompt,
            "model": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "tickers": tickers,
        }

        result: Dict[str, Any] = {
            "prompt": prompt,
            "market_data": market_data,
            "alpha_scores": alpha_scores,
            "fundamentals": fundamentals,
            "news": news_data,
            "mode": mode,
        }

        if mode == "auto":
            allocations = self._call_llm(prompt)
            if allocations:
                self._record_allocation(allocations)
                result["allocations"] = allocations
                result["success"] = True
            else:
                result["success"] = False
                result["error"] = "LLM call failed — see prompt for manual reasoning"

        return result

    # ── Data Fetching ──────────────────────────────────────────────────

    def _fetch_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes + price history + technical for each ticker."""
        data = {}
        for ticker in tickers:
            try:
                quote = get_quote(ticker)
                if "error" in quote:
                    print(f"  ⚠ {ticker}: {quote['error']}")
                    continue

                hist = get_history(ticker, period="6mo")
                price = quote["price"]

                # Update price history
                self.price_history[ticker].append(price)
                if len(self.price_history[ticker]) > 30:
                    self.price_history[ticker] = self.price_history[ticker][-30:]
                self._last_price[ticker] = price

                # Technical indicators
                close_series = hist["Close"]
                rsi_val = _safe_rsi(close_series)
                macd = _macd(close_series)
                bb = _bb(close_series)

                # SMA crosses
                sma_20 = _short_sma(hist, 20)
                sma_50 = _short_sma(hist, 50)
                sma_200 = _short_sma(hist, 200)

                data[ticker] = {
                    "price": price,
                    "change_pct": quote.get("change_pct", 0),
                    "volume": quote.get("volume", 0),
                    "52w_high": quote.get("52w_high", 0),
                    "52w_low": quote.get("52w_low", 0),
                    "pe_ratio": quote.get("pe_ratio"),
                    "rsi": rsi_val,
                    "macd": macd,
                    "bollinger": bb,
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                    "price_history": [
                        {"date": str(idx.date()), "price": round(row["Close"], 2)}
                        for idx, row in hist.tail(10).iterrows()
                    ],
                }
                print(f"  ✓ {ticker}: ₹{price} ({quote.get('change_pct', 0):+.1f}%)")
            except Exception as e:
                print(f"  ✗ {ticker}: {e}")

        return data

    def _fetch_alpha_scores(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Score each ticker with alpha zoo factors."""
        scores = {}
        for ticker in tickers:
            try:
                hist = get_history(ticker, period="6mo")
                price_data = _build_price_data(hist)
                if not price_data or len(price_data.get("close", [])) < 30:
                    scores[ticker] = {"error": "Insufficient history"}
                    continue
                result = score_all_alphas(price_data)
                scores[ticker] = result
            except Exception as e:
                scores[ticker] = {"error": str(e)}
        return scores

    def _fetch_fundamentals(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch fundamental scores for each ticker."""
        scores = {}
        for ticker in tickers:
            try:
                result = score_fundamentals(ticker)
                scores[ticker] = result
            except Exception as e:
                scores[ticker] = {"error": str(e)}
        return scores

    def _fetch_news_data(self, tickers: List[str]) -> Dict[str, List[Dict]]:
        """Fetch news for each ticker (2 articles each, MoneyControl + LiveMint)."""
        news = {}
        for ticker in tickers:
            ticker_news = []
            try:
                mc = get_moneycontrol_news(ticker, limit=2)
                lm = get_livemint_news(ticker, limit=2)
                ticker_news.extend(mc[:2])
                ticker_news.extend(lm[:2])
                # Filter out error entries
                ticker_news = [n for n in ticker_news if "source" in n and n.get("source") != "Error"]
            except Exception:
                pass
            news[ticker] = ticker_news[:3]
        return news

    # ── Prompt Construction ────────────────────────────────────────────

    def _prepare_market_analysis(self, market_data: Dict, alpha_scores: Dict) -> str:
        """Build market + alpha analysis section."""
        lines = ["## MARKET ANALYSIS"]
        lines.append("")

        for ticker, data in market_data.items():
            price = data.get("price", 0)
            change = data.get("change_pct", 0)
            rsi = data.get("rsi")
            alpha = alpha_scores.get(ticker, {})
            agg = alpha.get("aggregate", "N/A")
            signal = alpha.get("signal", "N/A")

            lines.append(f"### {ticker}")
            lines.append(f"- **Price:** ₹{price:,.2f} ({change:+.1f}%)")
            lines.append(f"- **52W Range:** ₹{data.get('52w_low', 0):,.0f} — ₹{data.get('52w_high', 0):,.0f}")
            if data.get("pe_ratio"):
                lines.append(f"- **PE Ratio:** {data['pe_ratio']:.1f}")
            if rsi is not None:
                rsi_label = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
                lines.append(f"- **RSI(14):** {rsi} ({rsi_label})")

            # Moving averages
            sma_20 = data.get("sma_20")
            sma_50 = data.get("sma_50")
            sma_200 = data.get("sma_200")
            if sma_20 and sma_50:
                trend_short = "bullish" if sma_20 > sma_50 else "bearish"
                lines.append(f"- **SMA 20/50:** {trend_short} (SMA20: ₹{sma_20:,.0f}, SMA50: ₹{sma_50:,.0f})")
            if sma_200:
                trend_long = "above" if price > sma_200 else "below"
                lines.append(f"- **SMA 200:** {trend_long} (₹{sma_200:,.0f})")

            # Bollinger
            bb = data.get("bollinger", {})
            if bb:
                lines.append(f"- **Bollinger:** {bb.get('signal', 'N/A')} (position: {bb.get('position_pct', 'N/A')}%)")

            # Alpha Zoo
            if isinstance(agg, (int, float)):
                theme_str = ""
                themes = alpha.get("themes", {})
                if themes:
                    top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
                    theme_str = " | ".join(f"{t}: {s:.0f}" for t, s in top_themes)
                lines.append(f"- **Alpha Zoo Score:** {agg}/100 ({signal})")
                if theme_str:
                    lines.append(f"- **Alpha Themes:** {theme_str}")
            elif alpha.get("error"):
                lines.append(f"- **Alpha Zoo:** Error ({alpha['error']})")

            # Price history
            price_hist = data.get("price_history", [])
            if price_hist:
                hist_str = " → ".join(f"₹{p['price']:,.0f}" for p in price_hist[-5:])
                lines.append(f"- **Recent Prices:** {hist_str}")

            lines.append("")

        return "\n".join(lines)

    def _prepare_fundamental_analysis(self, fundamentals: Dict) -> str:
        """Build fundamental analysis section."""
        lines = ["## FUNDAMENTAL ANALYSIS"]
        lines.append("")

        for ticker, data in fundamentals.items():
            if "error" in data:
                lines.append(f"### {ticker}: Data unavailable")
                continue

            score = data.get("overall_score", data.get("score", "N/A"))
            signals = data.get("signals", [])
            risks = data.get("risks", [])

            lines.append(f"### {ticker} — Score: {score}/100")
            if signals:
                for s in signals[:4]:
                    lines.append(f"- ✅ {s}")
            if risks:
                for r in risks[:3]:
                    lines.append(f"- ⚠️ {r}")
            lines.append("")

        return "\n".join(lines)

    def _prepare_news_analysis(self, tickers: List[str], news_data: Dict) -> str:
        """Build news analysis section."""
        lines = ["## RECENT NEWS"]
        lines.append("")

        has_news = False
        for ticker in tickers:
            articles = news_data.get(ticker, [])
            if articles:
                has_news = True
                lines.append(f"### {ticker}")
                for a in articles[:3]:
                    title = a.get("title", "No title")[:120]
                    source = a.get("source", "")
                    lines.append(f"- [{source}] {title}")
                lines.append("")

        if not has_news:
            lines.append("_No recent news available._")
            lines.append("")

        return "\n".join(lines)

    def _prepare_account_analysis(self) -> str:
        """Build portfolio/account history section."""
        lines = ["## PORTFOLIO STATUS"]
        lines.append("")

        total_value = self.cash_balance + sum(
            p.get("market_value", 0) for p in self.positions.values()
        )
        pnl = total_value - self.initial_cash
        pnl_pct = (pnl / self.initial_cash) * 100 if self.initial_cash > 0 else 0

        lines.append(f"- **Total Value:** ₹{total_value:,.0f}")
        lines.append(f"- **Cash:** ₹{self.cash_balance:,.0f}")
        lines.append(f"- **P&L:** ₹{pnl:+,.0f} ({pnl_pct:+.1f}%)")

        if self.positions:
            lines.append("")
            lines.append("### Current Holdings")
            for ticker, pos in self.positions.items():
                lines.append(f"- {ticker}: {pos.get('quantity', 0):.0f} shares @ ₹{pos.get('avg_price', 0):,.0f}")

        if self.previous_allocations:
            lines.append("")
            lines.append("### Previous Allocations")
            for asset, alloc in sorted(self.previous_allocations.items(),
                                       key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"- {asset}: {alloc*100:.1f}%")

        if self.allocation_history:
            lines.append("")
            lines.append("### Recent Performance")
            for snap in self.allocation_history[-3:]:
                ts = snap.get("timestamp", "")[:16]
                perf = snap.get("performance", 0)
                lines.append(f"- {ts}: {perf:+.1f}%")

        lines.append("")
        return "\n".join(lines)

    def _combine_analysis(self, market: str, fundamental: str,
                          news: str, account: str) -> str:
        """Combine all analysis sections (market → fundamental → news → account)."""
        return f"{market}\n{fundamental}\n{news}\n{account}"

    def _get_portfolio_prompt(self, analysis: str, tickers: List[str],
                              date: Optional[str] = None) -> str:
        """Build the full LLM prompt for portfolio allocation."""
        date_str = f"Today is {date}." if date else f"Today is {datetime.now().strftime('%Y-%m-%d')} (IST)."
        ticker_list = ", ".join(tickers)
        sample = tickers[:3] if len(tickers) >= 3 else tickers

        return f"""{date_str}

You are a professional portfolio manager specializing in Indian equities (NSE/BSE).
Analyze the provided market data, alpha signals, fundamentals, and news to produce an optimal portfolio allocation.

PORTFOLIO FRAMEWORK:
- Allocate across the available stocks + CASH
- Target: maximize risk-adjusted returns over 1-3 months
- Use CASH tactically (30-70%) for capital preservation in uncertain markets
- Diversify across sectors; avoid concentration > 25% in any single stock
- Prefer quality businesses (high Alpha Zoo + strong fundamentals) over pure momentum

{analysis}

AVAILABLE ASSETS: {ticker_list}, CASH

DECISION RULES:
1. Stocks with Alpha Zoo score > 65 + strong fundamentals → overweight (15-25% each)
2. Stocks with Alpha Zoo score 45-65 → neutral weight (5-15%)
3. Stocks with Alpha Zoo score < 45 or negative signals → underweight or skip
4. CASH allocation depends on market breadth:
   - Bullish breadth → 10-30% cash
   - Neutral breadth → 30-50% cash
   - Bearish breadth → 50-70% cash
5. Consider recent news sentiment — negative news should reduce allocation
6. Check RSI: > 70 = caution (wait for pullback), < 30 = opportunity

CRITICAL: Return ONLY valid JSON. No extra text.

REQUIRED JSON FORMAT:
{{
  "reasoning": "Brief 2-3 sentence explanation of your allocation strategy",
  "market_outlook": "Your view on current market conditions (bullish/neutral/bearish)",
  "top_convictions": ["Stock with highest conviction and why", "Second highest", "Third highest"],
  "key_risks": ["Risk 1 to be aware of", "Risk 2"],
  "allocations": {{
    "{sample[0] if len(sample) > 0 else 'RELIANCE'}": 0.15,
    "{sample[1] if len(sample) > 1 else 'TCS'}": 0.15,
    "{sample[2] if len(sample) > 2 else 'HDFCBANK'}": 0.10,
    "CASH": 0.60
  }}
}}

RULES:
1. Return ONLY the JSON object — no markdown, no backticks, no extra text
2. All allocation values must sum to exactly 1.0
3. CASH must be one of the allocation keys
4. Every available stock should appear in allocations (even if 0.0)
5. Use double quotes for all strings
6. No trailing commas
"""

    # ── LLM Calling ────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM via litellm (auto mode). Requires API keys in env."""
        try:
            import litellm

            messages = [{"role": "user", "content": prompt}]

            response = litellm.completion(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=4000,
            )

            content = response.choices[0].message.content
            self.last_llm_output = {
                "raw_response": content,
                "model": self.model_name,
                "timestamp": datetime.now().isoformat(),
            }

            # Parse JSON from response
            allocations = self._parse_allocation_response(content)
            return allocations

        except ImportError:
            print("⚠ litellm not installed. Use mode='prompt' instead.")
            return None
        except Exception as e:
            print(f"✗ LLM call failed: {e}")
            return None

    def _parse_allocation_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON allocations from LLM response."""
        try:
            # Try direct parse
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try extracting JSON from text
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    print(f"✗ Failed to parse JSON from LLM response")
                    return None
            else:
                print(f"✗ No JSON found in LLM response")
                return None

        if not isinstance(parsed, dict):
            return None

        if "allocations" not in parsed:
            # Maybe the whole dict IS the allocations
            if any(isinstance(v, (int, float)) for v in parsed.values()):
                parsed = {"allocations": parsed, "reasoning": "Direct allocation"}
            else:
                return None

        return parsed

    # ── Allocation Recording ───────────────────────────────────────────

    def _record_allocation(self, parsed: Dict[str, Any]) -> None:
        """Record allocation snapshot for history tracking."""
        allocs = parsed.get("allocations", {})

        # Normalize to sum to 1.0
        total = sum(v for v in allocs.values() if isinstance(v, (int, float)))
        if total > 0 and abs(total - 1.0) > 0.01:
            allocs = {k: v / total for k, v in allocs.items() if isinstance(v, (int, float))}

        self.previous_allocations = allocs.copy()

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "allocations": allocs,
            "reasoning": parsed.get("reasoning", ""),
            "market_outlook": parsed.get("market_outlook", ""),
            "top_convictions": parsed.get("top_convictions", []),
            "key_risks": parsed.get("key_risks", []),
        }
        self.allocation_history.append(snapshot)

    # ── Output Formatting ──────────────────────────────────────────────

    def format_allocation(self, result: Dict[str, Any]) -> str:
        """Format allocation result for display."""
        lines = []

        if result.get("mode") == "auto" and result.get("allocations"):
            alloc = result["allocations"]
            reasoning = alloc.get("reasoning", "")
            outlook = alloc.get("market_outlook", "")
            convictions = alloc.get("top_convictions", [])
            risks = alloc.get("key_risks", [])
            allocations = alloc.get("allocations", {})

            lines.append(f"\n{'='*60}")
            lines.append(f"🤖 {self.name} — Portfolio Allocation")
            lines.append(f"{'='*60}")
            lines.append("")

            if reasoning:
                lines.append(f"💭 **Reasoning:** {reasoning}")
                lines.append("")
            if outlook:
                lines.append(f"📊 **Market Outlook:** {outlook}")
                lines.append("")

            lines.append("### Allocations")
            for asset, pct in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(pct * 30)
                lines.append(f"  {asset:<12} {pct*100:>5.1f}%  {bar}")

            if convictions:
                lines.append("")
                lines.append("### Top Convictions")
                for i, c in enumerate(convictions, 1):
                    lines.append(f"  {i}. {c}")

            if risks:
                lines.append("")
                lines.append("### Key Risks")
                for r in risks:
                    lines.append(f"  ⚠️ {r}")

            lines.append(f"\n{'='*60}")

        elif result.get("prompt"):
            lines.append(f"\n{'='*60}")
            lines.append(f"🤖 {self.name} — Analysis Prompt (mode={result['mode']})")
            lines.append(f"{'='*60}")
            lines.append("")
            lines.append(result["prompt"])

        return "\n".join(lines)

    def get_performance_summary(self) -> str:
        """Get tracked performance summary."""
        if not self.allocation_history:
            return "No allocation history yet. Run analyze() first."

        lines = []
        lines.append(f"\n📈 {self.name} — Performance History")
        lines.append("=" * 50)

        for snap in self.allocation_history[-10:]:
            ts = snap.get("timestamp", "")[:16]
            outlook = snap.get("market_outlook", "N/A")
            allocs = snap.get("allocations", {})
            top = sorted(allocs.items(), key=lambda x: x[1], reverse=True)[:3]
            top_str = " | ".join(f"{a}: {p*100:.0f}%" for a, p in top)
            lines.append(f"  {ts} | {outlook:<10} | {top_str}")

        if len(self.allocation_history) > 10:
            lines.append(f"  ... ({len(self.allocation_history) - 10} more snapshots)")

        return "\n".join(lines)
