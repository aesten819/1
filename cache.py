import json
import sqlite3
import time

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
