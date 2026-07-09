import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

FMP_BASE = "https://financialmodelingprep.com/stable"
_API_KEY = None


def _key():
    global _API_KEY
    if _API_KEY is None:
        try:
            from decouple import config
            _API_KEY = config("FMP_API_KEY", default="")
        except ImportError:
            _API_KEY = os.environ.get("FMP_API_KEY", "")
    return _API_KEY


def fmp_get(endpoint, params=None):
    url = f"{FMP_BASE}{endpoint}"
    p = {"apikey": _key()}
    if params:
        p.update(params)
    resp = requests.get(url, params=p, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_one_quote(symbol):
    try:
        data = fmp_get("/quote", {"symbol": symbol})
        if isinstance(data, list) and data:
            return data[0]
    except Exception:
        pass
    return None


def get_quotes(symbols):
    """Fetch quotes for a list of symbols in parallel (Starter plan: no batch endpoint)."""
    if not symbols:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_one_quote, sym): sym for sym in symbols}
        for future in as_completed(futures):
            quote = future.result()
            if quote:
                results.append(quote)
    return results


def search_symbols(query, limit=15):
    try:
        results = fmp_get("/search-symbol", {"query": query, "limit": limit})
        if isinstance(results, list):
            return [
                {"symbol": r.get("symbol", ""), "name": r.get("name", "")}
                for r in results if r.get("symbol")
            ]
    except Exception:
        pass
    return []


def get_news(feed_type="stock", limit=20):
    """
    Fetch latest news from FMP stable API.
    feed_type: 'stock' | 'crypto'
    """
    endpoints = {
        "stock":  "/news/stock-latest",
        "crypto": "/news/crypto-latest",
    }
    endpoint = endpoints.get(feed_type, "/news/stock-latest")
    try:
        return fmp_get(endpoint, {"limit": limit})
    except Exception:
        return []


def get_profile(symbol):
    """Fetch company profile (description, sector, CEO, website)."""
    try:
        data = fmp_get("/profile", {"symbol": symbol})
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}
