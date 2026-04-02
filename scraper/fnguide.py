# scraper/fnguide.py
"""
FnGuide 컨센서스 및 예상 실적 스크래퍼.

데이터는 FnGuide HTML 페이지 내부 스크립트가 호출하는 JSON API로 가져온다.
주요 엔드포인트:
  - /SVO2/json/data/01_06/03_{code}.json  : 증권사별 적정주가 & 투자의견
  - /SVO2/json/data/01_06/04_{code}.json  : 리포트 요약 (최근 보고서별 추천의견)
  - /SVO2/json/data/01_06/01_{code}_A_D.json : 연간 컨센서스 실적
"""
import re
import json
import requests
from collections import defaultdict

BASE = "https://comp.fnguide.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://comp.fnguide.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# FnGuide RECOM_CD → opinion label
# 5 = 강력매수, 4 = 매수, 3 = 중립, 2 = 매도, 1 = 강력매도
_RECOM_BUY = {"5.00", "4.00", "BUY", "매수", "강력매수", "적극매수"}
_RECOM_HOLD = {"3.00", "HOLD", "NEUTRAL", "중립", "보유"}
_RECOM_SELL = {"2.00", "1.00", "SELL", "매도", "강력매도"}


def _get_json(path: str) -> dict | list | None:
    url = BASE + path
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.text.lstrip("\ufeff").strip()
        if not text or text.startswith("<"):
            return None
        return json.loads(text)
    except Exception as e:
        print(f"[FnGuide warning] {e}")
        return None


def _clean_num(text: str) -> int | None:
    """'256,720' or '256,720원' → 256720; '-100' → -100"""
    s = str(text).strip()
    sign = -1 if s.startswith("-") else 1
    digits = re.sub(r"[^\d]", "", s)
    return sign * int(digits) if digits else None


def _clean_float(text: str) -> float | None:
    s = re.sub(r"[^\d.\-]", "", str(text))
    try:
        return float(s)
    except ValueError:
        return None


def scrape_consensus(code: str) -> dict:
    """
    FnGuide 컨센서스 페이지에서 아래 데이터를 파싱해 반환:
      - consensus: target_price, upside_pct, opinion, buy/hold/sell 수
      - trend: [{"date": "YYYY-MM", "target_price": int}, ...]

    내부적으로 FnGuide JSON API를 사용한다:
      - 03_{code}.json : 증권사별 목표주가 (AVG_PRC = 컨센서스 평균, EST_DT = 추정일)
      - 04_{code}.json : 리포트별 투자의견 (RECOMMEND 필드, CLS_PRC = 현재가)
    """
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
        "current_price": None,
    }

    # --- 증권사별 목표주가 (jsonPath3) ---
    broker_data = _get_json(f"/SVO2/json/data/01_06/03_A{code}.json")
    if broker_data and "comp" in broker_data:
        items = broker_data["comp"]
        if items:
            # AVG_PRC는 전체 평균 컨센서스 목표주가 (모든 row 동일값)
            result["consensus"]["target_price"] = _clean_num(items[0].get("AVG_PRC", ""))

            # 월별 추세: EST_DT 기준 월별 평균 목표주가
            monthly: dict[str, list[int]] = defaultdict(list)
            for item in items:
                est_dt = item.get("EST_DT", "")   # "YYYY/MM/DD"
                tp_str = item.get("TARGET_PRC", "").replace(",", "").strip()
                if est_dt and tp_str:
                    month = est_dt[:7].replace("/", "-")   # "YYYY-MM"
                    try:
                        monthly[month].append(int(tp_str))
                    except ValueError:
                        pass

            result["trend"] = [
                {"date": m, "target_price": sum(ps) // len(ps)}
                for m, ps in sorted(monthly.items())
            ]

            # RECOM_CD 기반 매수/중립/매도 집계
            for item in items:
                cd = item.get("RECOM_CD", "").strip()
                if cd in _RECOM_BUY:
                    result["consensus"]["buy"] += 1
                elif cd in _RECOM_HOLD:
                    result["consensus"]["hold"] += 1
                elif cd in _RECOM_SELL:
                    result["consensus"]["sell"] += 1

            # Track if broker table was populated
            broker_counted = bool(
                result["consensus"]["buy"] or
                result["consensus"]["hold"] or
                result["consensus"]["sell"]
            )
    else:
        broker_counted = False

    # --- 리포트별 투자의견 (jsonPath4) ---
    # 더 풍부한 RECOMMEND 텍스트 필드로 재집계 (broker 집계가 비어 있으면 대체)
    report_data = _get_json(f"/SVO2/json/data/01_06/04_A{code}.json")
    current_price: int | None = None
    if report_data and "comp" in report_data:
        r_items = report_data["comp"]
        if r_items:
            # 현재가
            current_price = _clean_num(r_items[0].get("CLS_PRC", ""))

            # 투자의견 집계 (broker 테이블이 비어 있을 경우 대체)
            if not broker_counted:
                for item in r_items:
                    rec = item.get("RECOMMEND", "").strip().upper()
                    if rec in {r.upper() for r in _RECOM_BUY}:
                        result["consensus"]["buy"] += 1
                    elif rec in {r.upper() for r in _RECOM_HOLD}:
                        result["consensus"]["hold"] += 1
                    elif rec in {r.upper() for r in _RECOM_SELL}:
                        result["consensus"]["sell"] += 1

    # --- upside_pct 계산 ---
    tp = result["consensus"]["target_price"]
    if tp and current_price and current_price > 0:
        result["consensus"]["upside_pct"] = round((tp - current_price) / current_price * 100, 2)
    result["current_price"] = current_price

    # --- 전체 투자의견 결정 ---
    total = (
        result["consensus"]["buy"]
        + result["consensus"]["hold"]
        + result["consensus"]["sell"]
    )
    if total > 0:
        buy_ratio = result["consensus"]["buy"] / total
        if buy_ratio >= 0.6:
            result["consensus"]["opinion"] = "매수"
        elif buy_ratio >= 0.3:
            result["consensus"]["opinion"] = "중립"
        else:
            result["consensus"]["opinion"] = "매도"

    return result


def scrape_earnings(code: str) -> list[dict]:
    """
    FnGuide 컨센서스 실적 JSON에서 예상 실적(연간) 파싱.
    반환: [{"year": "2026E", "revenue": int, "op_income": int, "eps": int}, ...]

    내부적으로 /SVO2/json/data/01_06/01_{code}_A_D.json 사용.
    """
    data = _get_json(f"/SVO2/json/data/01_06/01_A{code}_A_D.json")
    if not data or "comp" not in data:
        return []

    items = data["comp"]
    if not items:
        return []

    # 첫 번째 row가 헤더 (ACCOUNT_NM='항목', D_2~D_7 = 기간 레이블)
    header = items[0]
    # 추정치 컬럼만 추출: "(E)"가 포함된 컬럼
    estimate_cols = [
        (col, val)
        for col, val in header.items()
        if col.startswith("D_") and "(E)" in str(val)
    ]

    # 필요한 행 인덱싱
    rows_by_nm: dict[str, dict] = {}
    for item in items[1:]:
        nm = item.get("ACCOUNT_NM", "").strip()
        # 매출액, 영업이익, EPS 최상위 행만 (GB='0' or GB='')
        if item.get("GB") in ("0", ""):
            for key in ("매출액", "영업이익", "EPS"):
                if nm.startswith(key) and key not in rows_by_nm:
                    rows_by_nm[key] = item

    earnings: list[dict] = []
    for col, label in estimate_cols:
        # 예: "2026/12(E)" → "2026E"
        year = re.sub(r"/\d{2}\(E\)", "E", label)
        revenue = _clean_num(rows_by_nm["매출액"][col]) if "매출액" in rows_by_nm else None
        op_income = _clean_num(rows_by_nm["영업이익"][col]) if "영업이익" in rows_by_nm else None
        eps = _clean_num(rows_by_nm["EPS"][col]) if "EPS" in rows_by_nm else None
        if revenue or op_income:
            earnings.append({
                "year": year,
                "revenue": revenue,
                "op_income": op_income,
                "eps": eps,
            })

    return earnings
