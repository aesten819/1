import io
import os
import requests
import pandas as pd

DATA_PATH = "data/stocks.csv"
MAX_SEARCH_RESULTS = 10


def download_stocks() -> pd.DataFrame:
    """kind.krx.co.kr에서 전체 상장 종목 목록 다운로드 후 data/stocks.csv 저장."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(
            "https://kind.krx.co.kr/corpgeneral/corpList.do",
            params={"method": "download", "searchType": "13"},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        raw = pd.read_html(io.BytesIO(resp.content), encoding="euc-kr", header=0)[0]
        df = raw[["종목코드", "회사명"]].rename(columns={"종목코드": "code", "회사명": "name"})
        df["code"] = df["code"].astype(str).str.zfill(6)
        os.makedirs("data", exist_ok=True)
        df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
        print(f"[KRX] {len(df)}개 종목 다운로드 완료")
        return df
    except Exception as e:
        print(f"[KRX download error] {e}")
        return pd.DataFrame(columns=["code", "name"])


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
    matched = df[
        df["name"].str.contains(query, na=False, regex=False, case=False) |
        df["code"].str.contains(query, na=False, regex=False)
    ]
    return matched.head(MAX_SEARCH_RESULTS)[["code", "name"]].to_dict(orient="records")
