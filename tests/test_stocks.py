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
