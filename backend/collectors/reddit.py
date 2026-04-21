"""Reddit 수집기 — aiohttp 기반 (PRAW 대신 Reddit JSON API)"""

from __future__ import annotations

import json
import os
import uuid

import re

import aiohttp

from collectors.base import BaseCollector
from models.schemas import VocItem


class RedditCollector(BaseCollector):
    """Reddit JSON API로 게시물 + 댓글 수집 (API 키 불필요)"""

    USER_AGENT = "VOCCollector/0.1 (research)"

    # 관련성 필터 — 영어 관사/전치사/접속사만 제거 (제품명 키워드 보존)
    _STOP_WORDS = {
        'the', 'for', 'and', 'with', 'about', 'how', 'what', 'why',
        'when', 'where', 'reddit', 'has', 'have', 'had', 'are', 'was',
        'been', 'will', 'can', 'would', 'should', 'does', 'did',
        'this', 'that', 'from', 'they', 'them', 'you', 'your',
    }

    def _is_relevant(self, text: str, query: str) -> bool:
        """쿼리의 핵심 키워드가 게시물에 포함되는지 확인.
        최소 2개 이상의 키워드 매칭 필요 (1개만 매칭 시 관련 없을 가능성 높음)."""
        query_words = [
            w.lower().strip('?!.,')
            for w in query.split()
            if len(w) >= 3 and w.lower() not in self._STOP_WORDS
        ]
        if not query_words:
            return True
        text_lower = text.lower()
        match_count = sum(
            1 for w in query_words
            if re.search(r'\b' + re.escape(w) + r'\b', text_lower)
        )
        # 키워드가 2개 이상이면 최소 2개 매칭 필요, 1개면 1개 매칭
        min_matches = min(2, len(query_words))
        return match_count >= min_matches

    async def collect(
        self,
        query: str,
        context: str,
        max_results: int = 10,
        keywords: list[str] | None = None,
    ) -> list[VocItem]:
        items: list[VocItem] = []
        kw_lower = [k.lower() for k in (keywords or [])]

        async with aiohttp.ClientSession(
            headers={"User-Agent": self.USER_AGENT}
        ) as session:
            # Reddit 검색 API (JSON)
            search_url = "https://www.reddit.com/search.json"
            params = {
                "q": query,
                "sort": "relevance",
                "t": "year",
                "limit": min(max_results, 25),
            }

            try:
                async with session.get(
                    search_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
            except Exception:
                return []

            posts = data.get("data", {}).get("children", [])

            for post_wrapper in posts:
                post = post_wrapper.get("data", {})
                if not post:
                    continue

                # 본문이 있는 게시물만
                selftext = post.get("selftext", "").strip()
                title = post.get("title", "").strip()
                text = f"{title}\n{selftext}" if selftext else title

                if len(text) < 20:
                    continue

                # 쿼리와 관련 없는 게시물 필터링
                if not self._is_relevant(text, query):
                    continue

                # plan keywords와 추가 매칭 (있을 경우)
                if kw_lower:
                    text_lower = text.lower()
                    if not any(kw in text_lower for kw in kw_lower):
                        continue

                permalink = post.get("permalink", "")
                source_url = f"https://www.reddit.com{permalink}" if permalink else ""

                item = VocItem(
                    id=uuid.uuid4().hex[:12],
                    project_id="",
                    platform="reddit",
                    sentiment="neutral",  # synthesizer에서 확정
                    original_text=text[:1000],
                    translated_text="",
                    source_url=source_url,
                    author=post.get("author"),
                    date=self._format_date(post.get("created_utc")),
                    topics=[post.get("subreddit", "")],
                    confidence=0.85,  # Reddit 직접 수집이므로 높은 신뢰도
                    confidence_label="확실",
                    collection_method="tier1_api",
                )
                items.append(item)

                if len(items) >= max_results:
                    break

        return items

    @staticmethod
    def _format_date(utc_ts: float | None) -> str | None:
        if not utc_ts:
            return None
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(utc_ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
