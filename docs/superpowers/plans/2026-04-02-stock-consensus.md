# 증권사 컨센서스 조회 웹 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 종목명 검색 → 증권사 컨센서스(목표주가, 투자의견, 추세, 예상실적)를 보여주는 로컬 웹 앱

**Architecture:** FastAPI 백엔드가 FnGuide/WiseReport를 requests+BeautifulSoup으로 스크래핑하고 SQLite에 TTL 1시간 캐시. 프론트는 단일 index.html이 fetch API로 백엔드를 호출하고 Chart.js로 렌더링.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, requests, BeautifulSoup4, pandas, lxml, pykrx, pytest, Chart.js (CDN)

---

## 파일 구조

```
/
├── main.py                  # FastAPI 앱, 라우터 (/api/search, /api/consensus/{code})
├── stocks.py                # KRX 종목 목록 다운로드 + 검색
├── cache.py                 # SQLite 캐시 레이어 (TTL 1시간)
├── scraper/
│   ├── __init__.py          # 빈 파일
│   ├── fnguide.py           # FnGuide 스크래핑 (컨센서스 요약, 추세, 예상실적)
│   └── wisereport.py        # WiseReport 스크래핑 (증권사별 상세 투자의견)
├── static/
│   └── index.html           # 단일 페이지 프론트엔드
├── tests/
│   ├── test_cache.py
│   ├── test_stocks.py
│   └── test_main.py
├── data/                    # 자동 생성됨 — KRX 종목 CSV 저장 위치
└── requirements.txt
```

---

## Task 1: 프로젝트 설정

**Files:**
- Create: `requirements.txt`
- Create: `scraper/__init__.py`
- Create: `data/` 디렉토리

- [ ] **Step 1: requirements.txt 작성**

```
fastapi>=0.111.0
uvicorn>=0.29.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.2.0
pandas>=2.2.0
pykrx>=1.0.47
pytest>=8.2.0
httpx>=0.27.0
```

- [ ] **Step 2: 디렉토리 및 빈 파일 생성**

```bash
mkdir -p scraper data static tests
touch scraper/__init__.py
```

- [ ] **Step 3: 의존성 설치**

```bash
pip install -r requirements.txt
```

Expected: 에러 없이 설치 완료

- [ ] **Step 4: 커밋**

```bash
git init
git add requirements.txt scraper/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: KRX 종목 목록 + /api/search 엔드포인트

KRX 전체 종목 목록을 초기 1회 다운로드해 `data/stocks.csv`에 저장. 이후 CSV를 읽어 종목명 검색.

**Files:**
- Create: `stocks.py`
- Create: `tests/test_stocks.py`
- Create: `main.py` (검색 엔드포인트만 먼저)

- [ ] **Step 1: 테스트 작성**

`tests/test_stocks.py`:
```python
import pandas as pd
import pytest
from stocks import search_stocks, load_stocks

def test_search_returns_matching_stocks():
    # 실제 CSV가 없으면 임시 DataFrame으로 테스트
    sample = pd.DataFrame({"name": ["삼성전자", "삼성SDI", "LG전자"], "code": ["005930", "006400", "066570"]})
    results = search_stocks("삼성", df=sample)
    assert len(results) == 2
    assert results[0]["name"] == "삼성전자"
    assert results[0]["code"] == "005930"

def test_search_empty_query_returns_empty():
    sample = pd.DataFrame({"name": ["삼성전자"], "code": ["005930"]})
    results = search_stocks("", df=sample)
    assert results == []

def test_search_no_match_returns_empty():
    sample = pd.DataFrame({"name": ["삼성전자"], "code": ["005930"]})
    results = search_stocks("존재하지않는종목XYZ", df=sample)
    assert results == []
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_stocks.py -v
```

Expected: `ImportError: No module named 'stocks'`

- [ ] **Step 3: stocks.py 구현**

`stocks.py`:
```python
import os
import pandas as pd
from pykrx import stock as krx

DATA_PATH = "data/stocks.csv"


def download_stocks() -> pd.DataFrame:
    """KRX 전체 종목 목록 다운로드 후 data/stocks.csv 저장."""
    tickers_kospi = krx.get_market_ticker_list(market="KOSPI")
    tickers_kosdaq = krx.get_market_ticker_list(market="KOSDAQ")
    all_tickers = tickers_kospi + tickers_kosdaq

    rows = []
    for code in all_tickers:
        name = krx.get_market_ticker_name(code)
        rows.append({"code": code, "name": name})

    df = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    return df


def load_stocks() -> pd.DataFrame:
    """CSV가 있으면 읽기, 없으면 다운로드."""
    if not os.path.exists(DATA_PATH):
        return download_stocks()
    return pd.read_csv(DATA_PATH, dtype={"code": str})


def search_stocks(query: str, df: pd.DataFrame | None = None) -> list[dict]:
    """종목명으로 부분 검색. 최대 10건 반환."""
    if not query:
        return []
    if df is None:
        df = load_stocks()
    matched = df[df["name"].str.contains(query, na=False)]
    return matched.head(10)[["code", "name"]].to_dict(orient="records")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_stocks.py -v
```

Expected: 3개 테스트 PASS

- [ ] **Step 5: main.py — 검색 엔드포인트**

`main.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from stocks import search_stocks

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/search")
def api_search(q: str = ""):
    return search_stocks(q)
```

- [ ] **Step 6: 서버 기동 확인**

```bash
uvicorn main:app --reload
```

브라우저에서 `http://localhost:8000/api/search?q=삼성` 접속.  
Expected: `[{"code": "005930", "name": "삼성전자"}, ...]` JSON 응답

- [ ] **Step 7: 커밋**

```bash
git add stocks.py tests/test_stocks.py main.py
git commit -m "feat: KRX stock search endpoint"
```

---

## Task 3: SQLite 캐시 레이어

**Files:**
- Create: `cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_cache.py`:
```python
import time
import pytest
from cache import Cache


@pytest.fixture
def cache(tmp_path):
    return Cache(db_path=str(tmp_path / "test.db"))


def test_miss_returns_none(cache):
    assert cache.get("005930") is None


def test_set_and_get(cache):
    data = {"name": "삼성전자", "consensus": {"target_price": 90000}}
    cache.set("005930", data)
    result = cache.get("005930")
    assert result["name"] == "삼성전자"
    assert result["consensus"]["target_price"] == 90000


def test_expired_returns_none(cache):
    data = {"name": "삼성전자"}
    cache.set("005930", data, ttl_seconds=1)
    time.sleep(2)
    assert cache.get("005930") is None


def test_set_overwrites(cache):
    cache.set("005930", {"v": 1})
    cache.set("005930", {"v": 2})
    assert cache.get("005930")["v"] == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_cache.py -v
```

Expected: `ImportError: No module named 'cache'`

- [ ] **Step 3: cache.py 구현**

`cache.py`:
```python
import json
import sqlite3
import time
from datetime import datetime, timezone

DEFAULT_TTL = 3600  # 1시간


class Cache:
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS cache (
                    code TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )"""
            )

    def get(self, code: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data_json, fetched_at, ttl_seconds FROM cache WHERE code = ?",
                (code,),
            ).fetchone()
        if row is None:
            return None
        data_json, fetched_at, ttl_seconds = row
        if time.time() - fetched_at > ttl_seconds:
            return None
        return json.loads(data_json)

    def set(self, code: str, data: dict, ttl_seconds: int = DEFAULT_TTL):
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cache (code, data_json, fetched_at, ttl_seconds)
                   VALUES (?, ?, ?, ?)""",
                (code, json.dumps(data, ensure_ascii=False), time.time(), ttl_seconds),
            )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_cache.py -v
```

Expected: 4개 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add cache.py tests/test_cache.py
git commit -m "feat: SQLite cache with TTL"
```

---

## Task 4: FnGuide 스크래퍼

컨센서스 요약(목표주가, 투자의견 분포), 월별 추세, 예상 실적을 FnGuide에서 파싱.

> **주의:** FnGuide HTML 구조는 변경될 수 있음. 파싱이 안 될 경우 `soup.find_all("table")`로 테이블 목록을 출력해 인덱스 조정.

**Files:**
- Create: `scraper/fnguide.py`

- [ ] **Step 1: scraper/fnguide.py 작성**

`scraper/fnguide.py`:
```python
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://comp.fnguide.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def _get(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def _clean_num(text: str) -> int | None:
    """'92,000원' → 92000"""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _clean_float(text: str) -> float | None:
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def scrape_consensus(code: str) -> dict:
    """
    FnGuide 컨센서스 페이지에서 아래 데이터를 파싱해 반환:
      - consensus: target_price, upside_pct, opinion, buy/hold/sell 수
      - trend: [{"date": "YYYY-MM", "target_price": int}, ...]
    """
    url = (
        f"https://comp.fnguide.com/SVO2/asp/SVD_Consensus.asp"
        f"?pGB=1&gicode=A{code}&cID=&MenuYn=Y&ReportGB=&NewMenuID=108&stkGb=701"
    )
    soup = _get(url)

    result = {
        "consensus": {
            "target_price": None,
            "upside_pct": None,
            "opinion": None,
            "buy": 0,
            "hold": 0,
            "sell": 0,
        },
        "trend": [],
    }

    # --- 컨센서스 요약 파싱 ---
    # FnGuide 페이지의 첫 번째 주요 테이블에 목표주가, 투자의견 분포가 있음
    # 테이블을 순회하며 '목표주가' 키워드를 찾음
    tables = soup.find_all("table")
    for tbl in tables:
        text = tbl.get_text()
        if "목표주가" in text:
            rows = tbl.find_all("tr")
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                if not cells:
                    continue
                # 목표주가 행
                if "목표주가" in cells[0] and len(cells) > 1:
                    result["consensus"]["target_price"] = _clean_num(cells[1])
                # 괴리율 행
                if "괴리율" in cells[0] and len(cells) > 1:
                    result["consensus"]["upside_pct"] = _clean_float(cells[1])
                # 투자의견 행
                if "Strong Buy" in text or "매수" in text:
                    if len(cells) >= 4:
                        # 형식: [의견명, 수, 의견명, 수, ...] 또는 별도 행
                        pass
            break  # 첫 번째 매칭 테이블만 사용

    # 투자의견 분포: '매수', '중립', '매도' 개수 파싱
    # FnGuide는 보통 별도 div/table로 의견 분포를 표시
    for tag in soup.find_all(["td", "th"]):
        txt = tag.get_text(strip=True)
        if re.match(r"^\d+$", txt):
            prev = tag.find_previous_sibling()
            if prev:
                label = prev.get_text(strip=True)
                if "매수" in label or "Buy" in label:
                    result["consensus"]["buy"] = int(txt)
                elif "중립" in label or "Hold" in label:
                    result["consensus"]["hold"] = int(txt)
                elif "매도" in label or "Sell" in label:
                    result["consensus"]["sell"] = int(txt)

    # 전체 투자의견 결정
    total = result["consensus"]["buy"] + result["consensus"]["hold"] + result["consensus"]["sell"]
    if total > 0:
        buy_ratio = result["consensus"]["buy"] / total
        if buy_ratio >= 0.6:
            result["consensus"]["opinion"] = "매수"
        elif buy_ratio >= 0.3:
            result["consensus"]["opinion"] = "중립"
        else:
            result["consensus"]["opinion"] = "매도"

    # --- 월별 추세 파싱 ---
    # 날짜(YYYY-MM 형식)와 목표주가 숫자가 같은 행에 있는 테이블을 찾음
    for tbl in tables:
        rows = tbl.find_all("tr")
        trend_rows = []
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) >= 2 and re.match(r"\d{4}/\d{2}|\d{4}\.\d{2}", cells[0]):
                price = _clean_num(cells[1])
                if price:
                    date_str = cells[0].replace("/", "-").replace(".", "-")[:7]
                    trend_rows.append({"date": date_str, "target_price": price})
        if trend_rows:
            result["trend"] = trend_rows
            break

    return result


def scrape_earnings(code: str) -> list[dict]:
    """
    FnGuide 재무 페이지에서 예상 실적(연간) 파싱.
    반환: [{"year": "2026E", "revenue": int, "op_income": int, "eps": int}, ...]
    """
    url = (
        f"https://comp.fnguide.com/SVO2/asp/SVD_Finance.asp"
        f"?pGB=1&gicode=A{code}&cID=&MenuYn=Y&ReportGB=D&NewMenuID=103&stkGb=701"
    )
    soup = _get(url)
    earnings = []

    try:
        # pd.read_html로 전체 테이블 파싱 후 예상 실적 테이블 찾기
        tables = pd.read_html(str(soup), flavor="lxml")
        for df in tables:
            df_str = df.to_string()
            if "매출액" in df_str or "영업이익" in df_str:
                # 첫 행이 연도(YYYY/12, 2026E 등), 인덱스가 항목명인 테이블
                # 예상치 열만 추출 (E 붙은 열)
                for col in df.columns:
                    col_str = str(col)
                    if "E" in col_str or "/" in col_str:
                        year = col_str.replace("/12", "").strip()
                        row_revenue = df[df.iloc[:, 0].astype(str).str.contains("매출액", na=False)]
                        row_op = df[df.iloc[:, 0].astype(str).str.contains("영업이익", na=False)]
                        row_eps = df[df.iloc[:, 0].astype(str).str.contains("EPS", na=False)]

                        revenue = _clean_num(str(row_revenue[col].values[0])) if not row_revenue.empty else None
                        op_income = _clean_num(str(row_op[col].values[0])) if not row_op.empty else None
                        eps = _clean_num(str(row_eps[col].values[0])) if not row_eps.empty else None

                        if revenue or op_income:
                            earnings.append({
                                "year": year,
                                "revenue": revenue,
                                "op_income": op_income,
                                "eps": eps,
                            })
                break
    except Exception:
        pass  # 파싱 실패 시 빈 리스트 반환

    return earnings
```

- [ ] **Step 2: 통합 테스트 — 실제 FnGuide 호출**

```bash
python -c "
from scraper.fnguide import scrape_consensus, scrape_earnings
import json

# 삼성전자 (005930)
c = scrape_consensus('005930')
print('=== 컨센서스 ===')
print(json.dumps(c['consensus'], ensure_ascii=False, indent=2))
print('추세 샘플:', c['trend'][:3])

e = scrape_earnings('005930')
print('=== 예상실적 ===')
print(json.dumps(e[:3], ensure_ascii=False, indent=2))
"
```

Expected: 목표주가, 투자의견 수가 숫자로 출력됨.  
만약 값이 None이면 파싱 실패 — 아래 디버그 명령으로 HTML 구조 확인 후 파서 조정:

```bash
python -c "
import requests
from bs4 import BeautifulSoup
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://comp.fnguide.com/'}
r = requests.get('https://comp.fnguide.com/SVO2/asp/SVD_Consensus.asp?pGB=1&gicode=A005930&MenuYn=Y&NewMenuID=108&stkGb=701', headers=headers)
soup = BeautifulSoup(r.text, 'lxml')
for i, t in enumerate(soup.find_all('table')):
    print(f'--- Table {i} ---')
    print(t.get_text()[:200])
"
```

- [ ] **Step 3: 커밋**

```bash
git add scraper/fnguide.py
git commit -m "feat: FnGuide consensus and earnings scraper"
```

---

## Task 5: WiseReport 스크래퍼

증권사별 투자의견 상세(증권사명, 의견, 목표주가, 날짜)를 WiseReport에서 파싱.

**Files:**
- Create: `scraper/wisereport.py`

- [ ] **Step 1: scraper/wisereport.py 작성**

`scraper/wisereport.py`:
```python
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://comp.wisereport.co.kr/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

OPINION_MAP = {
    "강력매수": "매수", "적극매수": "매수", "매수": "매수",
    "buy": "매수", "strong buy": "매수", "outperform": "매수",
    "중립": "중립", "hold": "중립", "market perform": "중립", "neutral": "중립",
    "비중축소": "매도", "매도": "매도", "sell": "매도", "underperform": "매도",
}


def _normalize_opinion(raw: str) -> str:
    return OPINION_MAP.get(raw.strip().lower(), raw.strip())


def scrape_brokers(code: str) -> list[dict]:
    """
    WiseReport 투자의견 페이지에서 증권사별 상세 파싱.
    반환: [{"firm": str, "opinion": str, "target": int|None, "date": str}, ...]
    """
    url = f"https://comp.wisereport.co.kr/company/c1100001.aspx?cmp_cd={code}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    brokers = []

    # WiseReport 투자의견 테이블: 증권사 / 투자의견 / 목표주가 / 날짜 열 구조
    tables = soup.find_all("table")
    for tbl in tables:
        headers_row = tbl.find("tr")
        if not headers_row:
            continue
        headers_text = headers_row.get_text()
        # 투자의견 테이블 식별: '증권사' 또는 '투자의견' 헤더 포함
        if "증권사" not in headers_text and "투자의견" not in headers_text:
            continue

        col_names = [th.get_text(strip=True) for th in headers_row.find_all(["th", "td"])]
        # 열 인덱스 찾기
        idx_firm = next((i for i, c in enumerate(col_names) if "증권사" in c), None)
        idx_opinion = next((i for i, c in enumerate(col_names) if "투자의견" in c), None)
        idx_target = next((i for i, c in enumerate(col_names) if "목표" in c), None)
        idx_date = next((i for i, c in enumerate(col_names) if "날짜" in c or "일자" in c or "date" in c.lower()), None)

        if idx_firm is None or idx_opinion is None:
            continue

        for row in tbl.find_all("tr")[1:]:  # 헤더 행 스킵
            cells = row.find_all(["th", "td"])
            if len(cells) <= max(filter(None, [idx_firm, idx_opinion, idx_target, idx_date])):
                continue
            firm = cells[idx_firm].get_text(strip=True) if idx_firm is not None else ""
            opinion_raw = cells[idx_opinion].get_text(strip=True) if idx_opinion is not None else ""
            target_raw = cells[idx_target].get_text(strip=True) if idx_target is not None else ""
            date_raw = cells[idx_date].get_text(strip=True) if idx_date is not None else ""

            if not firm:
                continue

            target_digits = re.sub(r"[^\d]", "", target_raw)
            brokers.append({
                "firm": firm,
                "opinion": _normalize_opinion(opinion_raw),
                "target": int(target_digits) if target_digits else None,
                "date": date_raw,
            })
        break  # 첫 번째 매칭 테이블만 사용

    return brokers
```

- [ ] **Step 2: 통합 테스트 — 실제 WiseReport 호출**

```bash
python -c "
from scraper.wisereport import scrape_brokers
import json
brokers = scrape_brokers('005930')
print(f'증권사 수: {len(brokers)}')
print(json.dumps(brokers[:3], ensure_ascii=False, indent=2))
"
```

Expected: 증권사 목록이 리스트로 출력됨.  
빈 리스트가 나오면 아래로 HTML 구조 확인:

```bash
python -c "
import requests
from bs4 import BeautifulSoup
h = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://comp.wisereport.co.kr/'}
r = requests.get('https://comp.wisereport.co.kr/company/c1100001.aspx?cmp_cd=005930', headers=h)
soup = BeautifulSoup(r.text, 'lxml')
for i, t in enumerate(soup.find_all('table')):
    print(f'--- Table {i} ---')
    print(t.get_text()[:300])
"
```

- [ ] **Step 3: 커밋**

```bash
git add scraper/wisereport.py
git commit -m "feat: WiseReport broker opinion scraper"
```

---

## Task 6: /api/consensus 엔드포인트 완성

캐시 + FnGuide + WiseReport를 조합해 통합 응답 반환.

**Files:**
- Modify: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_main.py`:
```python
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MOCK_CONSENSUS = {
    "consensus": {"target_price": 92000, "upside_pct": 22.7, "opinion": "매수", "buy": 18, "hold": 3, "sell": 0},
    "trend": [{"date": "2026-01", "target_price": 90000}],
}
MOCK_EARNINGS = [{"year": "2026E", "revenue": 320000, "op_income": 42000, "eps": 5200}]
MOCK_BROKERS = [{"firm": "미래에셋", "opinion": "매수", "target": 95000, "date": "2026-03-28"}]


def test_consensus_returns_combined_data():
    with (
        patch("main.cache.get", return_value=None),
        patch("main.cache.set"),
        patch("main.scrape_consensus", return_value=MOCK_CONSENSUS),
        patch("main.scrape_earnings", return_value=MOCK_EARNINGS),
        patch("main.scrape_brokers", return_value=MOCK_BROKERS),
        patch("main.load_stocks") as mock_stocks,
    ):
        import pandas as pd
        mock_stocks.return_value = pd.DataFrame({"code": ["005930"], "name": ["삼성전자"]})
        resp = client.get("/api/consensus/005930")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "삼성전자"
        assert data["consensus"]["target_price"] == 92000
        assert len(data["brokers"]) == 1
        assert len(data["earnings"]) == 1


def test_consensus_cache_hit_skips_scraping():
    cached = {
        "name": "삼성전자",
        "current_price": None,
        "consensus": {"target_price": 92000, "upside_pct": 22.7, "opinion": "매수", "buy": 18, "hold": 3, "sell": 0},
        "brokers": [],
        "trend": [],
        "earnings": [],
    }
    with patch("main.cache.get", return_value=cached):
        resp = client.get("/api/consensus/005930")
        assert resp.status_code == 200
        assert resp.json()["name"] == "삼성전자"


def test_search_endpoint():
    with patch("main.search_stocks", return_value=[{"code": "005930", "name": "삼성전자"}]):
        resp = client.get("/api/search?q=삼성")
        assert resp.status_code == 200
        assert resp.json()[0]["code"] == "005930"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_main.py -v
```

Expected: ImportError 또는 missing route 에러

- [ ] **Step 3: main.py 완성**

`main.py`:
```python
from fastapi import FastAPI, HTTPException
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_main.py -v
```

Expected: 3개 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add main.py tests/test_main.py
git commit -m "feat: consensus API endpoint with cache integration"
```

---

## Task 7: 프론트엔드 (index.html)

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: static/index.html 작성**

`static/index.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>증권사 컨센서스</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Pretendard', -apple-system, sans-serif; background: #f5f6fa; color: #222; }
    .container { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
    h1 { font-size: 1.4rem; margin-bottom: 20px; color: #1a1a2e; }

    /* 검색 */
    .search-row { display: flex; gap: 8px; margin-bottom: 28px; }
    #searchInput { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; }
    #searchBtn { padding: 10px 20px; background: #2563eb; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
    #searchBtn:hover { background: #1d4ed8; }
    #suggestions { background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-top: 4px; display: none; }
    .suggestion-item { padding: 10px 14px; cursor: pointer; font-size: 0.95rem; }
    .suggestion-item:hover { background: #f0f4ff; }

    /* 카드 */
    .card { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .card h2 { font-size: 1rem; color: #555; margin-bottom: 14px; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .summary-item label { font-size: 0.8rem; color: #888; display: block; margin-bottom: 4px; }
    .summary-item .val { font-size: 1.4rem; font-weight: 700; }
    .val.up { color: #e03131; }
    .val.down { color: #1971c2; }
    .opinion-bar { display: flex; gap: 8px; margin-top: 10px; align-items: center; flex-wrap: wrap; }
    .badge { padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
    .badge.buy { background: #fff0f0; color: #e03131; }
    .badge.hold { background: #fff9db; color: #e67700; }
    .badge.sell { background: #e7f5ff; color: #1971c2; }

    /* 테이블 */
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { text-align: left; padding: 8px 10px; border-bottom: 2px solid #eee; color: #666; font-weight: 600; }
    td { padding: 8px 10px; border-bottom: 1px solid #f0f0f0; }
    tr:last-child td { border-bottom: none; }

    /* 상태 */
    #status { text-align: center; padding: 40px; color: #888; display: none; }
    #error { background: #fff5f5; color: #c92a2a; padding: 14px; border-radius: 8px; margin-bottom: 16px; display: none; }
    .spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid #ddd; border-top-color: #2563eb; border-radius: 50%; animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    #results { display: none; }
    .refresh-btn { float: right; font-size: 0.8rem; color: #2563eb; background: none; border: none; cursor: pointer; padding: 0; }
  </style>
</head>
<body>
<div class="container">
  <h1>증권사 컨센서스 조회</h1>

  <div class="search-row">
    <input id="searchInput" type="text" placeholder="종목명 검색 (예: 삼성전자)" autocomplete="off">
    <button id="searchBtn">검색</button>
  </div>
  <div id="suggestions"></div>

  <div id="error"></div>
  <div id="status"><div class="spinner"></div> 데이터 불러오는 중...</div>

  <div id="results">
    <!-- 요약 카드 -->
    <div class="card">
      <h2 id="stockTitle">—</h2>
      <div class="summary-grid">
        <div class="summary-item">
          <label>컨센서스 목표가</label>
          <div class="val" id="targetPrice">—</div>
        </div>
        <div class="summary-item">
          <label>괴리율</label>
          <div class="val" id="upsidePct">—</div>
        </div>
        <div class="summary-item">
          <label>투자의견</label>
          <div class="val" id="opinion">—</div>
        </div>
      </div>
      <div class="opinion-bar" id="opinionBar"></div>
    </div>

    <!-- 추세 차트 -->
    <div class="card">
      <h2>목표주가 추세
        <button class="refresh-btn" id="refreshBtn">↻ 새로고침</button>
      </h2>
      <canvas id="trendChart" height="80"></canvas>
      <div id="noTrend" style="display:none;color:#aaa;font-size:.9rem;padding:20px 0;">추세 데이터 없음</div>
    </div>

    <!-- 증권사별 상세 -->
    <div class="card">
      <h2>증권사별 투자의견</h2>
      <div id="brokersWrap">
        <table>
          <thead><tr><th>증권사</th><th>투자의견</th><th>목표주가</th><th>날짜</th></tr></thead>
          <tbody id="brokersBody"></tbody>
        </table>
        <div id="noBrokers" style="display:none;color:#aaa;font-size:.9rem;padding:20px 0;">데이터 없음</div>
      </div>
    </div>

    <!-- 예상 실적 -->
    <div class="card">
      <h2>예상 실적</h2>
      <div id="earningsWrap">
        <table>
          <thead><tr><th>연도</th><th>매출액(억)</th><th>영업이익(억)</th><th>EPS(원)</th></tr></thead>
          <tbody id="earningsBody"></tbody>
        </table>
        <div id="noEarnings" style="display:none;color:#aaa;font-size:.9rem;padding:20px 0;">데이터 없음</div>
      </div>
    </div>
  </div>
</div>

<script>
let trendChart = null;
let currentCode = null;

const $ = id => document.getElementById(id);

// --- 검색 자동완성 ---
$('searchInput').addEventListener('input', async e => {
  const q = e.target.value.trim();
  if (!q) { hideSuggestions(); return; }
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
  const items = await res.json();
  showSuggestions(items);
});

$('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') { hideSuggestions(); loadConsensus(currentCode || null, $('searchInput').value); }
});
$('searchBtn').addEventListener('click', () => { hideSuggestions(); loadConsensus(currentCode || null, $('searchInput').value); });
$('refreshBtn').addEventListener('click', () => { if (currentCode) loadConsensus(currentCode, null, true); });

function showSuggestions(items) {
  const box = $('suggestions');
  if (!items.length) { hideSuggestions(); return; }
  box.innerHTML = items.map(it =>
    `<div class="suggestion-item" data-code="${it.code}" data-name="${it.name}">${it.name} <span style="color:#aaa;font-size:.85em">${it.code}</span></div>`
  ).join('');
  box.style.display = 'block';
  box.querySelectorAll('.suggestion-item').forEach(el => {
    el.addEventListener('click', () => {
      $('searchInput').value = el.dataset.name;
      currentCode = el.dataset.code;
      hideSuggestions();
      loadConsensus(currentCode);
    });
  });
}

function hideSuggestions() { $('suggestions').style.display = 'none'; }

// --- 컨센서스 로드 ---
async function loadConsensus(code, name, refresh = false) {
  if (!code && !name) return;

  // code가 없으면 검색 결과의 첫 번째 항목 사용
  if (!code && name) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(name)}`);
    const items = await res.json();
    if (!items.length) { showError('검색 결과 없음'); return; }
    code = items[0].code;
    $('searchInput').value = items[0].name;
  }

  currentCode = code;
  showLoading();

  try {
    const url = `/api/consensus/${code}${refresh ? '?refresh=true' : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderConsensus(data);
  } catch (err) {
    showError('데이터를 불러오지 못했습니다: ' + err.message);
  }
}

function renderConsensus(data) {
  hideLoading();
  $('results').style.display = 'block';
  $('error').style.display = 'none';

  // 요약
  $('stockTitle').textContent = data.name || '—';
  const tp = data.consensus?.target_price;
  $('targetPrice').textContent = tp ? tp.toLocaleString() + '원' : '—';
  const up = data.consensus?.upside_pct;
  const upEl = $('upsidePct');
  upEl.textContent = up != null ? (up > 0 ? '+' : '') + up.toFixed(1) + '%' : '—';
  upEl.className = 'val ' + (up > 0 ? 'up' : up < 0 ? 'down' : '');
  $('opinion').textContent = data.consensus?.opinion || '—';

  // 투자의견 분포
  const bar = $('opinionBar');
  const { buy = 0, hold = 0, sell = 0 } = data.consensus || {};
  bar.innerHTML = '';
  if (buy) bar.innerHTML += `<span class="badge buy">매수 ${buy}</span>`;
  if (hold) bar.innerHTML += `<span class="badge hold">중립 ${hold}</span>`;
  if (sell) bar.innerHTML += `<span class="badge sell">매도 ${sell}</span>`;

  // 추세 차트
  const trend = data.trend || [];
  if (trend.length) {
    $('noTrend').style.display = 'none';
    const canvas = $('trendChart');
    canvas.style.display = 'block';
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: trend.map(t => t.date),
        datasets: [{
          label: '컨센서스 목표주가',
          data: trend.map(t => t.target_price),
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { ticks: { callback: v => v.toLocaleString() } }
        }
      }
    });
  } else {
    $('trendChart').style.display = 'none';
    $('noTrend').style.display = 'block';
  }

  // 증권사별 테이블
  const brokers = data.brokers || [];
  const tbody = $('brokersBody');
  if (brokers.length) {
    $('noBrokers').style.display = 'none';
    tbody.innerHTML = brokers.map(b => `
      <tr>
        <td>${b.firm}</td>
        <td><span class="badge ${opClass(b.opinion)}">${b.opinion}</span></td>
        <td>${b.target ? b.target.toLocaleString() + '원' : '—'}</td>
        <td>${b.date || '—'}</td>
      </tr>`).join('');
  } else {
    $('noBrokers').style.display = 'block';
    tbody.innerHTML = '';
  }

  // 예상 실적 테이블
  const earnings = data.earnings || [];
  const etbody = $('earningsBody');
  if (earnings.length) {
    $('noEarnings').style.display = 'none';
    etbody.innerHTML = earnings.map(e => `
      <tr>
        <td>${e.year}</td>
        <td>${e.revenue != null ? e.revenue.toLocaleString() : '—'}</td>
        <td>${e.op_income != null ? e.op_income.toLocaleString() : '—'}</td>
        <td>${e.eps != null ? e.eps.toLocaleString() : '—'}</td>
      </tr>`).join('');
  } else {
    $('noEarnings').style.display = 'block';
    etbody.innerHTML = '';
  }
}

function opClass(op) {
  if (!op) return '';
  if (op.includes('매수') || op.toLowerCase().includes('buy')) return 'buy';
  if (op.includes('매도') || op.toLowerCase().includes('sell')) return 'sell';
  return 'hold';
}

function showLoading() {
  $('status').style.display = 'block';
  $('results').style.display = 'none';
  $('error').style.display = 'none';
}
function hideLoading() { $('status').style.display = 'none'; }
function showError(msg) {
  hideLoading();
  $('error').textContent = msg;
  $('error').style.display = 'block';
}

document.addEventListener('click', e => {
  if (!e.target.closest('#suggestions') && !e.target.closest('#searchInput')) hideSuggestions();
});
</script>
</body>
</html>
```

- [ ] **Step 2: 전체 통합 테스트 — 서버 기동 후 브라우저 확인**

```bash
uvicorn main:app --reload
```

브라우저에서 `http://localhost:8000` 접속:
1. "삼성전자" 검색 → 자동완성 드롭다운 확인
2. 항목 클릭 → 로딩 스피너 후 데이터 렌더링 확인
3. 목표주가 추세 차트 표시 확인
4. 증권사별 테이블, 예상 실적 테이블 확인
5. "↻ 새로고침" 버튼으로 캐시 무시 재조회 확인

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 전체 PASS

- [ ] **Step 4: 최종 커밋**

```bash
git add static/index.html
git commit -m "feat: frontend with search, consensus summary, trend chart, and earnings table"
```

---

## 실행 방법 요약

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 기동 (첫 실행 시 KRX 종목 목록 자동 다운로드)
uvicorn main:app --reload

# 브라우저에서 접속
open http://localhost:8000
```
