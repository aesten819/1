import re
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://comp.wisereport.co.kr/",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
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

    Data source: /company/ajax/CmpTrend.aspx?type=CmpList (JSON API)
    Fields used: BRK_NM, RECOMM, TARGET_PRC, ANL_DT
    """
    ajax_url = "https://comp.wisereport.co.kr/company/ajax/CmpTrend.aspx"
    headers = {**HEADERS, "Referer": f"https://comp.wisereport.co.kr/company/c1100001.aspx?cmp_cd={code}"}

    payload = {
        "type": "CmpList",
        "cmp_cd": code,
        "order_item": "",
        "order_typ": "D",
        "term_typ": 2,
    }

    try:
        resp = requests.post(ajax_url, headers=headers, data=payload, timeout=15)
        resp.raise_for_status()
        json_data = resp.json()
    except (ValueError, requests.exceptions.JSONDecodeError) as e:
        print(f"[WiseReport warning] Invalid JSON response for code {code}: {e}")
        return []
    except Exception as e:
        print(f"[WiseReport warning] {e}")
        return []

    rows = json_data.get("data") or []

    brokers = []
    for item in rows:
        firm = item.get("BRK_NM", "").strip()
        if not firm:
            continue

        opinion_raw = item.get("RECOMM", "")
        target_raw = item.get("TARGET_PRC", "")
        date_raw = item.get("ANL_DT", "")

        target_digits = re.sub(r"[^\d]", "", str(target_raw))

        brokers.append({
            "firm": firm,
            "opinion": _normalize_opinion(opinion_raw),
            "target": int(target_digits) if target_digits else None,
            "date": date_raw,
        })

    return brokers
