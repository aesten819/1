from unittest.mock import patch
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
