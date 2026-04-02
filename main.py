from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from stocks import search_stocks, load_stocks
from cache import Cache
from scraper.fnguide import scrape_consensus, scrape_earnings
from scraper.wisereport import scrape_brokers

app = FastAPI()
cache = Cache()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/api/search")
def api_search(q: str = ""):
    return search_stocks(q)


@app.get("/api/consensus/{code}")
def api_consensus(code: str, refresh: bool = False):
    if not refresh:
        cached = cache.get(code)
        if cached:
            return cached

    # 종목명 조회
    df = load_stocks()
    match = df[df["code"] == code]
    name = match["name"].values[0] if not match.empty else code

    # 스크래핑 (각각 실패해도 나머지는 반환)
    consensus_data = {"target_price": None, "upside_pct": None, "opinion": None, "buy": 0, "hold": 0, "sell": 0}
    trend = []
    earnings = []
    brokers = []

    try:
        fn = scrape_consensus(code)
        consensus_data = fn["consensus"]
        trend = fn["trend"]
    except Exception as e:
        print(f"[FnGuide consensus error] {code}: {e}")

    try:
        earnings = scrape_earnings(code)
    except Exception as e:
        print(f"[FnGuide earnings error] {code}: {e}")

    try:
        brokers = scrape_brokers(code)
    except Exception as e:
        print(f"[WiseReport error] {code}: {e}")

    result = {
        "name": name,
        "current_price": None,
        "consensus": consensus_data,
        "brokers": brokers,
        "trend": trend,
        "earnings": earnings,
    }

    cache.set(code, result)
    return result
