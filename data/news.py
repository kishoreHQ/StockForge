"""StockForge Data Layer - Financial news from Indian sources."""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json


def get_moneycontrol_news(symbol: str = None, limit: int = 10) -> list:
    """Fetch latest news from MoneyControl."""
    news = []
    
    try:
        if symbol:
            url = f"https://www.moneycontrol.com/news/tags/{symbol.lower()}.html"
        else:
            url = "https://www.moneycontrol.com/news/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        
        articles = soup.find_all("a", href=True)
        seen = set()
        for article in articles:
            href = article.get("href", "")
            title = article.get_text(strip=True)
            if (title and len(title) > 20 and 
                "/news/" in href and 
                title not in seen and
                len(news) < limit):
                seen.add(title)
                news.append({
                    "title": title,
                    "url": href if href.startswith("http") else f"https://www.moneycontrol.com{href}",
                    "source": "MoneyControl",
                })
    except Exception as e:
        news.append({"title": f"Error fetching MoneyControl: {e}", "source": "Error"})
    
    return news[:limit]


def get_livemint_news(symbol: str = None, limit: int = 5) -> list:
    """Fetch latest news from LiveMint."""
    news = []
    
    try:
        if symbol:
            url = f"https://www.livemint.com/search?query={symbol}"
        else:
            url = "https://www.livemint.com/latest-news"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        
        headlines = soup.find_all("h2")
        for h in headlines:
            a = h.find("a", href=True)
            if a:
                title = a.get_text(strip=True)
                href = a["href"]
                if title and len(title) > 15 and len(news) < limit:
                    news.append({
                        "title": title,
                        "url": href if href.startswith("http") else f"https://www.livemint.com{href}",
                        "source": "LiveMint",
                    })
    except Exception:
        pass
    
    return news[:limit]


def get_market_news_summary(limit: int = 10) -> list:
    """Get combined market news from multiple sources."""
    all_news = []
    
    # Try MoneyControl first
    mc_news = get_moneycontrol_news(limit=limit)
    all_news.extend(mc_news)
    
    # Add some from LiveMint
    lm_news = get_livemint_news(limit=5)
    all_news.extend(lm_news)
    
    # Deduplicate by title similarity
    seen = set()
    unique = []
    for item in all_news:
        key = item["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    return unique[:limit]


def analyze_sentiment(headlines: list) -> dict:
    """Simple sentiment analysis on headlines using keyword scoring."""
    positive_words = [
        "rally", "surge", "gain", "rise", "up", "bullish", "buy", "upgrade",
        "profit", "growth", "record", "high", "strong", "beat", "positive",
        "recovery", "boom", "jump", "soar", "outperform", "upgrade"
    ]
    negative_words = [
        "fall", "drop", "crash", "down", "bearish", "sell", "downgrade",
        "loss", "decline", "low", "weak", "miss", "negative", "selloff",
        "recession", "slump", "plunge", "underperform", "downgrade", "risk"
    ]
    
    scores = []
    for item in headlines:
        title = item.get("title", "").lower()
        score = 0
        pos_hits = [w for w in positive_words if w in title]
        neg_hits = [w for w in negative_words if w in title]
        score = len(pos_hits) - len(neg_hits)
        scores.append({
            "title": item.get("title", ""),
            "score": score,
            "positive": pos_hits,
            "negative": neg_hits,
            "sentiment": "positive" if score > 0 else ("negative" if score < 0 else "neutral"),
        })
    
    total_score = sum(s["score"] for s in scores)
    overall = "positive" if total_score > 0 else ("negative" if total_score < 0 else "neutral")
    
    return {
        "overall_sentiment": overall,
        "total_score": total_score,
        "articles_analyzed": len(scores),
        "breakdown": scores,
    }
