"""YouTube 수집기 — YouTube Data API v3 댓글 수집"""

from __future__ import annotations

import os
import uuid

import aiohttp

from collectors.base import BaseCollector
from models.schemas import VocItem


class YouTubeCollector(BaseCollector):
    """YouTube Data API v3로 동영상 댓글 수집"""

    API_BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")

    async def collect(
        self,
        query: str,
        context: str,
        max_results: int = 10,
        keywords: list[str] | None = None,
    ) -> list[VocItem]:
        if not self.api_key:
            raise RuntimeError(
                "YouTube API 키가 설정되지 않았습니다. 설정 → YouTube API 키 발급 방법을 참고하세요."
            )

        items: list[VocItem] = []
        kw_lower = [k.lower() for k in (keywords or [])]

        async with aiohttp.ClientSession() as session:
            # 1. 동영상 검색
            video_ids = await self._search_videos(session, query, max_videos=3)
            if not video_ids:
                return []

            # 2. 각 동영상의 댓글 수집
            per_video = max(max_results // len(video_ids), 5)
            for video_id, video_title in video_ids:
                comments = await self._fetch_comments(
                    session, video_id, video_title, per_video
                )
                # 키워드 사전 필터
                if kw_lower:
                    comments = [
                        c for c in comments
                        if any(kw in c.original_text.lower() for kw in kw_lower)
                    ]
                items.extend(comments)
                if len(items) >= max_results:
                    break

        return items[:max_results]

    async def _search_videos(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_videos: int = 3,
    ) -> list[tuple[str, str]]:
        """쿼리로 동영상 검색 → [(video_id, title), ...]"""
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_videos,
            "order": "relevance",
            "key": self.api_key,
        }
        try:
            async with session.get(
                f"{self.API_BASE}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    err = data.get("error", {})
                    raise RuntimeError(f"YouTube Search API 오류: {err.get('message', resp.status)}")

            return [
                (
                    item["id"]["videoId"],
                    item["snippet"].get("title", ""),
                )
                for item in data.get("items", [])
                if item.get("id", {}).get("videoId")
            ]
        except RuntimeError:
            raise
        except Exception:
            return []

    async def _fetch_comments(
        self,
        session: aiohttp.ClientSession,
        video_id: str,
        video_title: str,
        max_comments: int,
    ) -> list[VocItem]:
        """동영상 댓글 수집 → VocItem 목록"""
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_comments, 100),
            "order": "relevance",
            "key": self.api_key,
        }
        try:
            async with session.get(
                f"{self.API_BASE}/commentThreads",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 403:
                    # 댓글 비활성화된 동영상
                    return []
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

        items = []
        for thread in data.get("items", []):
            comment = thread.get("snippet", {}).get("topLevelComment", {})
            snippet = comment.get("snippet", {})

            text = snippet.get("textDisplay", "").strip()
            if len(text) < 10:
                continue

            author = snippet.get("authorDisplayName", "")
            published_at = snippet.get("publishedAt", "")
            date = published_at[:10] if published_at else None

            source_url = f"https://www.youtube.com/watch?v={video_id}"

            item = VocItem(
                id=uuid.uuid4().hex[:12],
                project_id="",
                platform="youtube",
                sentiment="neutral",  # synthesizer에서 확정
                original_text=text[:1000],
                translated_text="",
                source_url=source_url,
                author=author or None,
                date=date,
                topics=[],
                confidence=0.9,  # YouTube 공식 API, 높은 신뢰도
                confidence_label="확실",
                collection_method="tier1_api",
            )
            items.append(item)

        return items
