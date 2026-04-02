# 증권사 컨센서스 조회 웹 — 설계 문서

**날짜:** 2026-04-02  
**용도:** 개인 로컬 사용 (localhost)  
**스택:** FastAPI + HTML/JS + Chart.js

---

## 1. 개요

종목명을 검색하면 증권사 컨센서스 동향(목표주가, 투자의견, 추세, 예상 실적)을 한 화면에서 보여주는 로컬 웹 애플리케이션.

---

## 2. 아키텍처

```
[브라우저 - index.html]
        ↕ HTTP (localhost:8000)
[FastAPI 백엔드]
    ├── GET /api/search?q={종목명}
    └── GET /api/consensus/{code}
         ↕ HTTP 스크래핑
    [FnGuide Company Guide]   ← 컨센서스, 목표주가, 예상실적
    [WiseReport 기업모니터]    ← 증권사별 투자의견 상세
         ↕
    [SQLite 캐시]             ← TTL 1시간
```

### 파일 구조

```
/
├── main.py              # FastAPI 앱, 라우터
├── scraper/
│   ├── fnguide.py       # FnGuide 스크래핑 (컨센서스, 예상실적)
│   └── wisereport.py    # WiseReport 스크래핑 (증권사별 상세)
├── cache.py             # SQLite 캐시 레이어 (TTL 1시간)
└── static/
    └── index.html       # 단일 페이지 프론트엔드
```

---

## 3. API 엔드포인트

### `GET /api/search?q={종목명}`
- KRX 종목 목록에서 종목명 → 종목코드 검색
- 응답: `[{"code": "005930", "name": "삼성전자"}, ...]`

### `GET /api/consensus/{code}`
- 종목코드로 FnGuide + WiseReport 스크래핑 후 통합 반환
- 캐시 히트 시 스크래핑 없이 즉시 반환
- `?refresh=true` 파라미터로 캐시 무시하고 강제 재스크래핑

**응답 구조:**
```json
{
  "name": "삼성전자",
  "current_price": 75000,
  "consensus": {
    "target_price": 92000,
    "upside_pct": 22.7,
    "opinion": "매수",
    "buy": 18,
    "hold": 3,
    "sell": 0
  },
  "brokers": [
    {
      "firm": "미래에셋",
      "opinion": "매수",
      "target": 95000,
      "date": "2026-03-28"
    }
  ],
  "trend": [
    {"date": "2025-01", "target_price": 88000}
  ],
  "earnings": [
    {
      "year": "2026E",
      "revenue": 320000,
      "op_income": 42000,
      "eps": 5200
    }
  ]
}
```

---

## 4. 스크래핑 대상

| 데이터 | 출처 | URL 패턴 |
|---|---|---|
| 컨센서스 요약, 목표주가 추세 | FnGuide Company Guide | `comp.fnguide.com/SVO2/asp/SVD_Consensus.asp?gicode=A{code}` |
| 예상 실적 | FnGuide Company Guide | `comp.fnguide.com/SVO2/asp/SVD_Finance.asp?gicode=A{code}` |
| 증권사별 투자의견 상세 | WiseReport 기업모니터 | `comp.wisereport.co.kr/company/c1100001.aspx?cmp_cd={code}` |
| 종목코드 목록 | KRX 공공데이터 | 초기 1회 다운로드 후 로컬 저장 |

---

## 5. 캐시 설계

- **저장소:** SQLite (`cache.db`)
- **스키마:** `cache(code TEXT PRIMARY KEY, data_json TEXT, fetched_at TIMESTAMP)`
- **TTL:** 1시간
- **강제 갱신:** `?refresh=true` 쿼리 파라미터

---

## 6. 프론트엔드 화면 구성

단일 `index.html`, 섹션 구성:

1. **검색창** — 종목명 입력 + 검색 버튼
2. **요약 카드** — 현재가, 컨센서스 목표가, 괴리율, 투자의견 분포
3. **목표주가 추세 차트** — Chart.js 꺾은선 그래프 (월별)
4. **증권사별 상세 테이블** — 증권사 / 투자의견 / 목표가 / 날짜
5. **예상 실적 테이블** — 연도별 매출 / 영업이익 / EPS

로딩 스피너, 에러 메시지 표시 포함.

---

## 7. 예외 처리

| 상황 | 처리 |
|---|---|
| 스크래핑 차단/실패 | 캐시 있으면 캐시 반환, 없으면 에러 메시지 표시 |
| 종목코드 없음 | "검색 결과 없음" 표시 |
| 일부 데이터 누락 | 해당 섹션만 "데이터 없음" 표시, 나머지 정상 표시 |
| FnGuide 구조 변경 | 스크래퍼 수동 수정 필요 (알려진 한계) |

---

## 8. 알려진 한계

- FnGuide/WiseReport HTML 구조 변경 시 스크래퍼 수정 필요
- 소형주·비커버리지 종목은 컨센서스 데이터 없을 수 있음
- 스크래핑은 ToS 위반 가능성 있음 (개인 용도로만 사용)
