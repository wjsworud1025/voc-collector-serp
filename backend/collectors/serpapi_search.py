"""SerpApi.com 기반 검색 수집기 — Google CSE 대체 + Credit 보호 4계층.

4계층 보호 순서:
1. SERPAPI_DRY_RUN=1 → fixture JSON 반환 (개발/테스트용, 0 credits)
2. 로컬 SQLite 7일 캐시 hit → 캐시 반환 (0 credits)
3. /account.json 가드 → 잔여 < SERPAPI_MIN_CREDITS_GUARD면 차단
4. 실제 SerpApi 호출 (1 credit) → 성공 시 로컬 캐시 저장
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import aiohttp

from collectors.base import BaseCollector, BROWSER_HEADERS
from collectors.serpapi_cache import SerpApiCache
from collectors.serpapi_engine_configs import (
    SERPAPI_ENGINES,
    build_engine_params,
    extract_url_tuples,
)
from collectors.web_reader import WebReader
from models.schemas import VocItem

logger = logging.getLogger(__name__)

# fixture 디렉터리 — DRY_RUN 모드에서 사용
_FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "serpapi"


class SerpApiSearchCollector(BaseCollector):
    """SerpApi → 페이지 fetch → LLM 추출. Credit 보호 4계층 통합."""

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY", "")
        self.dry_run = os.getenv("SERPAPI_DRY_RUN", "0") == "1"
        self.min_credits_guard = int(os.getenv("SERPAPI_MIN_CREDITS_GUARD", "5"))
        # serpapi_cache.db는 voc.db와 별도 → 손상 시 voc 데이터 안전
        cache_db = Path(os.getenv("SERPAPI_CACHE_DB", "data/serpapi_cache.db"))
        self.cache = SerpApiCache(cache_db)
        self.web_reader = WebReader()

    async def collect(
        self,
        query: str,
        context: str,
        max_results: int = 10,
        keywords: Optional[list[str]] = None,
        engine: str = "google",
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        lr: Optional[str] = None,
    ) -> list[VocItem]:
        """SerpApi 검색 → 각 결과 페이지에서 VOC 추출.

        engine: 사용할 SerpApi 엔진 (google, naver, yahoo_jp, yandex, baidu,
                ebay, walmart, home_depot, google_shopping, amazon)
        """
        params = build_engine_params(engine, query, max_results, self.api_key, gl, hl, lr)
        raw = await self._search_with_protection(params)
        url_tuples = extract_url_tuples(engine, raw)

        if not url_tuples:
            logger.warning(
                "[serpapi] no results engine=%s q='%s'", engine, query[:60]
            )
            return []

        items: list[VocItem] = []
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            for url, title, snippet in url_tuples:
                try:
                    page_items = await self.web_reader.extract_from_url_with_session(
                        session,
                        url,
                        context,
                        keywords=keywords or [],
                        title_hint=title,
                        snippet_hint=snippet,
                    )
                    # platform 설정: 엔진명 사용 (google → web, 나머지는 엔진명 그대로)
                    for item in page_items:
                        item.platform = engine if engine != "google" else item.platform
                    items.extend(page_items)
                except Exception as e:
                    logger.debug(
                        "[serpapi] page extract failed engine=%s url=%s err=%s",
                        engine, url[:80], e,
                    )

        logger.info(
            "[serpapi] collect done engine=%s q='%s' urls=%d items=%d",
            engine, query[:60], len(url_tuples), len(items),
        )
        return items

    # ── _build_params는 내부 호환성 유지용 (신규 코드는 build_engine_params 사용) ──

    # ── 4계층 Credit 보호 ────────────────────────────────────────────────

    async def _search_with_protection(self, params: dict) -> dict:
        """DRY_RUN → 로컬 캐시 → account 가드 → 실제 호출."""

        # 계층 4 (DRY_RUN): fixture 반환
        if self.dry_run:
            q = params.get("q") or params.get("query") or params.get("p") or params.get("text") or params.get("_nkw") or params.get("k", "")
            logger.info("[serpapi-dryrun] engine=%s q='%s'", params.get("engine", "google"), str(q)[:60])
            return self._load_fixture(params)

        # 계층 3 (로컬 캐시): 7일 이내 동일 쿼리
        cached = self.cache.get(params)
        if cached is not None:
            logger.info("[serpapi-cache] HIT q='%s'", params.get("q", "")[:60])
            return cached

        # 계층 1 (account 가드): 잔여 credits 확인
        remaining = await self._check_account()
        if remaining < self.min_credits_guard:
            logger.error(
                "[serpapi-guard] credits %d < threshold %d — search BLOCKED",
                remaining, self.min_credits_guard,
            )
            return {
                "error": (
                    f"SerpApi credits exhausted ({remaining} left, "
                    f"threshold {self.min_credits_guard}). "
                    "Please upgrade your plan or wait until monthly reset."
                )
            }

        # 실제 호출 (계층 2: SerpApi 자체 1시간 캐시는 no_cache=false로 자동 활용)
        try:
            from serpapi import GoogleSearch  # type: ignore[import]
            data: dict = await asyncio.to_thread(
                lambda: GoogleSearch(params).get_dict()
            )
        except Exception as e:
            logger.error("[serpapi-call] EXCEPTION q='%s' err=%s", params.get("q", "")[:60], e)
            return {"error": str(e)}

        if "error" in data:
            logger.error("[serpapi-call] API ERROR: %s", data["error"])
            return data

        # 성공 시 로컬 캐시 저장
        self.cache.set(params, data)

        # 호출 후 잔여 재확인 (관찰성 로그)
        new_remaining = await self._check_account()
        logger.info(
            "[serpapi-call] SUCCESS q='%s' results=%d remaining=%d consumed=%d",
            params.get("q", "")[:60],
            len(data.get("organic_results", [])),
            new_remaining,
            remaining - new_remaining,
        )
        return data

    async def _check_account(self) -> int:
        """`/account.json` 호출 (무료 엔드포인트). total_searches_left 반환."""
        if not self.api_key:
            return 0
        url = f"https://serpapi.com/account.json?api_key={self.api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        logger.warning("[serpapi-account] HTTP %d", resp.status)
                        # fail-open: 가드 실패 시 검색 진행 (가드 장애로 운영 차단 방지)
                        return self.min_credits_guard + 1
                    account = await resp.json()
                    return int(account.get("total_searches_left", 0))
        except Exception as e:
            logger.warning("[serpapi-account] check failed: %s", e)
            return self.min_credits_guard + 1  # fail-open

    def _load_fixture(self, params: dict) -> dict:
        """DRY_RUN 모드: 엔진+gl 일치 fixture 우선, 없으면 gl, 없으면 any organic."""
        engine = params.get("engine", "google")
        gl = params.get("gl", "us")

        # Priority 1: {engine}_{gl}_*.json  (예: naver_kr_*.json, ebay_us_*.json)
        candidates = sorted(_FIXTURE_DIR.glob(f"{engine}_{gl}_*.json"))
        # Priority 2: {gl}_*organic*.json  (기존 구글 픽스처)
        if not candidates:
            candidates = sorted(_FIXTURE_DIR.glob(f"{gl}_*organic*.json"))
        # Priority 3: {engine}_*.json  (엔진명 일치, 임의 지역)
        if not candidates:
            candidates = sorted(_FIXTURE_DIR.glob(f"{engine}_*.json"))
        # Priority 4: *organic*.json  (아무 organic 픽스처)
        if not candidates:
            candidates = sorted(_FIXTURE_DIR.glob("*organic*.json"))
        if not candidates:
            empty_path = _FIXTURE_DIR / "empty_organic_results.json"
            if empty_path.exists():
                return json.loads(empty_path.read_text(encoding="utf-8"))
            return {"organic_results": [], "search_metadata": {"status": "DRY_RUN"}}

        chosen = candidates[0]
        logger.info(
            "[serpapi-dryrun] fixture=%s engine=%s gl=%s", chosen.name, engine, gl
        )
        return json.loads(chosen.read_text(encoding="utf-8"))
