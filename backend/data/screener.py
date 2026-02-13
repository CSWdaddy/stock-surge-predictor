from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import yfinance as yf

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# Broad base list: large-cap, mid-cap, popular retail, high-beta, sector ETFs
DEFAULT_CANDIDATES = [
    # Mega cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "AVGO", "CRM",
    # High-beta / retail favorites
    "PLTR", "SOFI", "NIO", "RIVN", "LCID", "MARA", "RIOT", "COIN", "SQ", "SHOP",
    "SNAP", "PINS", "RBLX", "U", "DKNG", "HOOD", "AFRM", "UPST", "PATH", "IONQ",
    # Semis & AI
    "AMD", "INTC", "MU", "MRVL", "ARM", "SMCI", "TSM", "QCOM", "ON", "ASML",
    # Cloud / SaaS
    "CRWD", "ZS", "NET", "SNOW", "ABNB", "DDOG", "MDB", "PANW", "OKTA", "CFLT",
    # Biotech / pharma (volatile)
    "MRNA", "BNTX", "CELH", "HIMS", "DNLI", "SAVA",
    # Consumer / travel / industrial
    "PYPL", "DIS", "BA", "F", "GM", "UAL", "DAL", "CCL", "NCLH", "RCL",
    "WMT", "COST", "TGT", "NKE", "SBUX", "MCD",
    # Energy / commodities
    "XOM", "CVX", "OXY", "FSLR", "ENPH", "LI",
    # Financials
    "JPM", "GS", "C", "BAC", "V", "MA",
    # ETFs (market pulse)
    "SPY", "QQQ", "IWM", "XLE", "XLF", "ARKK", "SOXL", "TQQQ",
]


def _scrape_finviz(filters: str, label: str, max_results: int = 40) -> List[str]:
    """Generic FINVIZ screener scraper with pagination."""
    tickers = []
    try:
        for start in range(1, max_results + 1, 20):  # FINVIZ pages by 20
            url = f"https://finviz.com/screener.ashx?v=111&f={filters}&ft=4&o=-change&r={start}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", {"class": "table-light"})
            if not table:
                break

            rows = table.find_all("tr")[1:]
            if not rows:
                break

            for row in rows:
                cols = row.find_all("td")
                if len(cols) > 1:
                    ticker_link = cols[1].find("a")
                    if ticker_link:
                        tickers.append(ticker_link.text.strip())

            if len(rows) < 20:  # last page
                break
    except Exception:
        pass

    return tickers[:max_results]


def get_unusual_volume_stocks() -> List[str]:
    """Stocks with relative volume > 2x and avg volume > 500K."""
    return _scrape_finviz("sh_avgvol_o500,sh_relvol_o2", "unusual_volume", 40)


def get_gap_up_stocks() -> List[str]:
    """Stocks gapping up > 3%."""
    return _scrape_finviz("sh_avgvol_o500,ta_gap_u3", "gap_up", 30)


def get_new_high_stocks() -> List[str]:
    """Stocks near 52-week high (within 5%)."""
    return _scrape_finviz("sh_avgvol_o500,ta_highlow52w_nh", "new_high", 30)


def get_oversold_bounce_stocks() -> List[str]:
    """RSI oversold (<30) stocks that might bounce."""
    return _scrape_finviz("sh_avgvol_o500,ta_rsi_os30", "oversold", 30)


def get_top_gainers() -> List[str]:
    """Today's top gainers (>5% change)."""
    return _scrape_finviz("sh_avgvol_o500,ta_change_u5", "top_gainers", 30)


def get_high_volatility_stocks() -> List[str]:
    """High weekly volatility stocks."""
    return _scrape_finviz("sh_avgvol_o500,ta_volatility_wo6", "high_vol", 20)


def get_yahoo_trending() -> List[str]:
    """Get trending tickers from Yahoo Finance."""
    try:
        url = "https://finance.yahoo.com/trending-tickers"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        tickers = []
        for link in soup.find_all("a", {"data-test": "quoteLink"}):
            t = link.text.strip()
            if t and t.isalpha() and len(t) <= 5:
                tickers.append(t)
        return tickers[:20]
    except Exception:
        return []


def get_candidate_tickers():
    # type: () -> tuple
    """Get combined list of candidate tickers from all screening sources.

    Returns (ticker_list, sources_dict).

    Sources:
    1. FINVIZ unusual volume (거래량 급증)
    2. FINVIZ gap-up (갭업 종목)
    3. FINVIZ new 52w high (신고가 근접)
    4. FINVIZ oversold bounce (과매도 반등)
    5. FINVIZ top gainers (오늘 급등)
    6. FINVIZ high volatility (고변동성)
    7. Yahoo trending
    8. Default popular stock list
    """
    candidates = set()
    sources = {}

    screeners = [
        ("unusual_volume", get_unusual_volume_stocks),
        ("gap_up", get_gap_up_stocks),
        ("new_high", get_new_high_stocks),
        ("oversold_bounce", get_oversold_bounce_stocks),
        ("top_gainers", get_top_gainers),
        ("high_volatility", get_high_volatility_stocks),
        ("yahoo_trending", get_yahoo_trending),
    ]

    for name, func in screeners:
        try:
            result = func()
            sources[name] = len(result)
            candidates.update(result)
        except Exception:
            sources[name] = 0

    # Always include defaults as base coverage
    candidates.update(DEFAULT_CANDIDATES)
    sources["default_list"] = len(DEFAULT_CANDIDATES)

    ticker_list = sorted(candidates)

    return ticker_list, sources


def get_candidate_tickers_simple() -> List[str]:
    """Simplified version that returns just the ticker list."""
    tickers, _ = get_candidate_tickers()
    return tickers
