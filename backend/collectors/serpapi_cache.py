"""SerpApi 응답 로컬 캐시 — credit 절약 핵심 인프라.

설계 원칙:
- voc.db와 분리된 별도 SQLite (serpapi_cache.db) — 손상 시 voc 데이터에 영향 없음
- 캐시 키는 q + gl + hl + lr + num + device + engine 해시 (api_key 제외 → 키 교체에도 재사용)
- 기본 TTL 7일 — SerpApi 자체 캐시 1시간보다 훨씬 길게 보호
- 동기 SQLite (검색 호출은 어차피 동기 SDK라 async 불필요)
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SerpApiCache:
    """파일 기반 SQLite 캐시 — 7일 영구 보관."""

    DEFAULT_TTL_SECONDS = 7 * 86400  # 7일

    def __init__(self, db_path: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.db_path = Path(db_path)
        self.ttl = ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS serpapi_cache (
                    key TEXT PRIMARY KEY,
                    params_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    cached_at INTEGER NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_age ON serpapi_cache(cached_at)"
            )

    @staticmethod
    def _hash_params(params: dict) -> str:
        """캐시 키 해시 — api_key 제외하여 키 교체에도 재사용."""
        cache_params = {k: v for k, v in params.items() if k != "api_key"}
        normalized = json.dumps(cache_params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    def get(self, params: dict) -> Optional[dict]:
        """7일 이내 캐시 hit이면 응답 반환, 없으면 None."""
        key = self._hash_params(params)
        cutoff = int(time.time()) - self.ttl
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT response_json FROM serpapi_cache "
                    "WHERE key = ? AND cached_at >= ?",
                    (key, cutoff),
                ).fetchone()
                if row:
                    # hit_count 증가 (관찰성)
                    conn.execute(
                        "UPDATE serpapi_cache SET hit_count = hit_count + 1 WHERE key = ?",
                        (key,),
                    )
                    return json.loads(row[0])
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning("[serpapi-cache] get failed key=%s err=%s", key[:16], e)
        return None

    def set(self, params: dict, response: dict) -> None:
        """응답을 캐시에 저장 (REPLACE)."""
        key = self._hash_params(params)
        params_log = {k: v for k, v in params.items() if k != "api_key"}
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO serpapi_cache "
                    "(key, params_json, response_json, cached_at, hit_count) "
                    "VALUES (?, ?, ?, ?, 0)",
                    (
                        key,
                        json.dumps(params_log, ensure_ascii=False),
                        json.dumps(response, ensure_ascii=False),
                        int(time.time()),
                    ),
                )
        except sqlite3.Error as e:
            logger.warning("[serpapi-cache] set failed key=%s err=%s", key[:16], e)

    def stats(self) -> dict:
        """캐시 통계 — 디버깅/관찰성 용도."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*), MIN(cached_at), MAX(cached_at), SUM(hit_count) "
                    "FROM serpapi_cache"
                ).fetchone()
            return {
                "entries": row[0] or 0,
                "oldest_at": row[1],
                "newest_at": row[2],
                "total_hits": row[3] or 0,
            }
        except sqlite3.Error as e:
            logger.warning("[serpapi-cache] stats failed: %s", e)
            return {"entries": 0, "oldest_at": None, "newest_at": None, "total_hits": 0}

    def purge_expired(self) -> int:
        """TTL 만료 항목 제거. 제거된 행 수 반환."""
        cutoff = int(time.time()) - self.ttl
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    "DELETE FROM serpapi_cache WHERE cached_at < ?", (cutoff,)
                )
                return cur.rowcount
        except sqlite3.Error as e:
            logger.warning("[serpapi-cache] purge failed: %s", e)
            return 0
