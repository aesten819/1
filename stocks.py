import os
import pandas as pd
from pykrx import stock as krx

DATA_PATH = "data/stocks.csv"


def _today_str() -> str:
    from datetime import date
    return date.today().strftime("%Y%m%d")


def download_stocks() -> pd.DataFrame:
    """KRX 전체 종목 목록 다운로드 후 data/stocks.csv 저장."""
    date_str = _today_str()
    tickers_kospi = krx.get_market_ticker_list(date_str, market="KOSPI")
    tickers_kosdaq = krx.get_market_ticker_list(date_str, market="KOSDAQ")

    all_tickers = tickers_kospi + tickers_kosdaq

    rows = []
    for code in all_tickers:
        name = krx.get_market_ticker_name(code)
        rows.append({"code": code, "name": name})

    df = pd.DataFrame(rows, columns=["code", "name"])
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    return df


def load_stocks() -> pd.DataFrame:
    """CSV가 있으면 읽기, 없으면 다운로드.
    CSV가 비어있거나 필요한 열이 없으면 다운로드를 재시도한다."""
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH, dtype={"code": str})
        if "name" in df.columns and "code" in df.columns and len(df) > 0:
            return df
    return download_stocks()


def search_stocks(query: str, df: pd.DataFrame | None = None) -> list[dict]:
    """종목명으로 부분 검색. 최대 10건 반환."""
    if not query:
        return []
    if df is None:
        df = load_stocks()
    if df.empty or "name" not in df.columns:
        return []
    matched = df[df["name"].str.contains(query, na=False)]
    return matched.head(10)[["code", "name"]].to_dict(orient="records")
