import os
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta

analyzer = SentimentIntensityAnalyzer()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

EMPTY_NEWS = {"score": 50, "headline_count": 0, "avg_sentiment": 0, "headlines": [], "source": "none"}
EMPTY_SOCIAL = {"score": 50, "mention_count": 0, "avg_sentiment": 0, "source": "none"}


def _score_headlines(headlines):
    """Run VADER on a list of headlines, return (scores_list, avg, normalized_0_100)."""
    if not headlines:
        return [], 0, 50
    scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    avg = sum(scores) / len(scores)
    normalized = (avg + 1) * 50
    return scores, round(avg, 3), round(normalized, 1)


# ─── News Sources (no API key needed) ──────────────────────────────────────


def analyze_yfinance_news(ticker: str) -> dict:
    """Get news from yfinance (Yahoo Finance) - free, no key required."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
            return EMPTY_NEWS.copy()

        headlines = []
        for item in news[:15]:
            title = item.get("title", "")
            if not title:
                # newer yfinance versions nest under 'content'
                content = item.get("content", {})
                title = content.get("title", "") if isinstance(content, dict) else ""
            if title:
                headlines.append(title)

        if not headlines:
            return EMPTY_NEWS.copy()

        _, avg, normalized = _score_headlines(headlines)
        return {
            "score": normalized,
            "headline_count": len(headlines),
            "avg_sentiment": avg,
            "headlines": headlines[:5],
            "source": "yahoo_finance",
        }
    except Exception:
        return EMPTY_NEWS.copy()


def analyze_finviz_news(ticker: str) -> dict:
    """Scrape news headlines from Finviz - free, no key required."""
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}&p=d"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return EMPTY_NEWS.copy()

        soup = BeautifulSoup(resp.text, "html.parser")
        news_table = soup.find("table", {"id": "news-table"})
        if not news_table:
            return EMPTY_NEWS.copy()

        headlines = []
        for row in news_table.find_all("tr")[:15]:
            link = row.find("a")
            if link and link.text.strip():
                headlines.append(link.text.strip())

        if not headlines:
            return EMPTY_NEWS.copy()

        _, avg, normalized = _score_headlines(headlines)
        return {
            "score": normalized,
            "headline_count": len(headlines),
            "avg_sentiment": avg,
            "headlines": headlines[:5],
            "source": "finviz",
        }
    except Exception:
        return EMPTY_NEWS.copy()


def analyze_newsapi(ticker: str) -> dict:
    """NewsAPI - only used when API key is configured."""
    if not NEWSAPI_KEY:
        return EMPTY_NEWS.copy()
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "from": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "apiKey": NEWSAPI_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return EMPTY_NEWS.copy()

        articles = resp.json().get("articles", [])
        headlines = [a["title"] for a in articles if a.get("title")]

        if not headlines:
            return EMPTY_NEWS.copy()

        _, avg, normalized = _score_headlines(headlines)
        return {
            "score": normalized,
            "headline_count": len(headlines),
            "avg_sentiment": avg,
            "headlines": headlines[:5],
            "source": "newsapi",
        }
    except Exception:
        return EMPTY_NEWS.copy()


# ─── Social Sources ─────────────────────────────────────────────────────────


def analyze_stocktwits(ticker: str) -> dict:
    """StockTwits API - free, no auth required."""
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return EMPTY_SOCIAL.copy()

        data = resp.json()
        messages = data.get("messages", [])
        if not messages:
            return {**EMPTY_SOCIAL, "source": "stocktwits"}

        sentiments = []
        texts = []
        bullish_count = 0
        bearish_count = 0

        for msg in messages[:30]:
            body = msg.get("body", "")
            if body:
                texts.append(body)
                score = analyzer.polarity_scores(body)
                sentiments.append(score["compound"])

            # StockTwits has built-in sentiment labels
            st_sentiment = msg.get("entities", {}).get("sentiment", {})
            if st_sentiment:
                if st_sentiment.get("basic") == "Bullish":
                    bullish_count += 1
                elif st_sentiment.get("basic") == "Bearish":
                    bearish_count += 1

        if not sentiments:
            return {**EMPTY_SOCIAL, "source": "stocktwits"}

        avg = sum(sentiments) / len(sentiments)

        # Blend VADER score with StockTwits native sentiment
        vader_normalized = (avg + 1) * 50
        total_labeled = bullish_count + bearish_count
        if total_labeled > 0:
            native_score = (bullish_count / total_labeled) * 100
            # 50/50 blend
            blended = vader_normalized * 0.5 + native_score * 0.5
        else:
            blended = vader_normalized

        return {
            "score": round(blended, 1),
            "mention_count": len(sentiments),
            "avg_sentiment": round(avg, 3),
            "bullish": bullish_count,
            "bearish": bearish_count,
            "top_posts": texts[:3],
            "source": "stocktwits",
        }
    except Exception:
        return {**EMPTY_SOCIAL, "source": "stocktwits_error"}


def analyze_reddit_sentiment(ticker: str) -> dict:
    """Reddit public JSON API (rate-limited but no auth)."""
    try:
        url = f"https://www.reddit.com/search.json"
        params = {"q": f"{ticker} stock", "sort": "new", "limit": 25, "t": "week"}
        resp = requests.get(url, headers={
            "User-Agent": "StockSurgePredictor/2.0 (educational project)"
        }, params=params, timeout=10)

        if resp.status_code != 200:
            return {**EMPTY_SOCIAL, "source": "reddit_unavailable"}

        posts = resp.json().get("data", {}).get("children", [])
        if not posts:
            return {**EMPTY_SOCIAL, "source": "reddit"}

        sentiments = []
        titles = []
        for post in posts:
            title = post.get("data", {}).get("title", "")
            if title and ticker.upper() in title.upper():
                score = analyzer.polarity_scores(title)
                sentiments.append(score["compound"])
                titles.append(title)

        if not sentiments:
            return {**EMPTY_SOCIAL, "source": "reddit"}

        avg = sum(sentiments) / len(sentiments)
        normalized = (avg + 1) * 50

        return {
            "score": round(normalized, 1),
            "mention_count": len(sentiments),
            "avg_sentiment": round(avg, 3),
            "top_posts": titles[:3],
            "source": "reddit",
        }
    except Exception:
        return {**EMPTY_SOCIAL, "source": "reddit_error"}


# ─── Combined Score ─────────────────────────────────────────────────────────


def get_combined_sentiment(ticker: str) -> dict:
    """Combine all sentiment sources with weighted scoring."""

    # Try multiple news sources, use the one with most data
    yf_news = analyze_yfinance_news(ticker)
    finviz_news = analyze_finviz_news(ticker)
    newsapi_news = analyze_newsapi(ticker)

    # Pick the news source with the most headlines
    news_sources = [yf_news, finviz_news, newsapi_news]
    news = max(news_sources, key=lambda s: s["headline_count"])

    # Social: try both StockTwits and Reddit
    stocktwits = analyze_stocktwits(ticker)
    reddit = analyze_reddit_sentiment(ticker)

    # Pick the social source with more mentions
    social = stocktwits if stocktwits.get("mention_count", 0) >= reddit.get("mention_count", 0) else reddit

    # Weighted combination
    has_news = news["headline_count"] > 0
    has_social = social.get("mention_count", 0) > 0

    if has_news and has_social:
        combined_score = news["score"] * 0.55 + social["score"] * 0.45
    elif has_news:
        combined_score = news["score"]
    elif has_social:
        combined_score = social["score"]
    else:
        combined_score = 50  # neutral fallback

    return {
        "score": round(combined_score, 1),
        "news": news,
        "social": social,
        # Keep reddit/stocktwits detail for the frontend
        "reddit": reddit,
        "stocktwits": stocktwits,
    }
