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
