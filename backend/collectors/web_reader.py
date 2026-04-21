"""웹페이지 읽기 + VOC 추출 — 할루시네이션 차단 핵심"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from collectors.base import BaseCollector, BROWSER_HEADERS
from models.schemas import VocItem
from google import genai

logger = logging.getLogger(__name__)


class WebReader(BaseCollector):
    """실제 페이지를 fetch하고 LLM에 텍스트만 전달하여 VOC 추출
    (LLM은 URL 접근 안 함 → 할루시네이션 원천 차단)"""

    MAX_TEXT_CHARS = 15000  # 페이지 하단 리뷰 손실 방지

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)
        from config import GEMINI_MODEL
        self._gemini_model = GEMINI_MODEL

    async def collect(
        self, query: str, context: str, max_results: int = 10
    ) -> list[VocItem]:
        # WebReader는 URL을 직접 받아 처리 (다른 수집기가 URL을 전달)
        return []

    async def extract_from_url(self, url: str, context: str,
                               keywords: Optional[list[str]] = None) -> list[VocItem]:
        """단일 URL에서 VOC 추출"""
        async with aiohttp.ClientSession() as session:
            return await self.extract_from_url_with_session(
                session, url, context, keywords=keywords or []
            )

    async def extract_from_url_with_session(
        self,
        session: aiohttp.ClientSession,
        url: str,
        context: str,
        keywords: Optional[list[str]] = None,
        title_hint: str = "",
        snippet_hint: str = "",
    ) -> list[VocItem]:
        """세션 재사용 버전 — SerpApiSearchCollector 위임 호출용.

        serpapi_search.py에서 aiohttp.ClientSession을 공유하여 커넥션 풀 효율화.
        """
        try:
            async with session.get(
                url,
                headers=BROWSER_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True,
            ) as resp:
                if resp.status not in (200, 203):
                    logger.debug("[web_reader] skip url=%s status=%d", url[:80], resp.status)
                    return []
                html = await resp.text(errors="replace")
        except Exception as e:
            logger.debug("[web_reader] fetch failed url=%s err=%s", url[:80], e)
            return []

        text = self._html_to_text(html)
        if len(text) < 50:
            return []

        items = await self._extract_from_text(
            text, url, context, keywords=keywords or [],
            title_hint=title_hint, snippet_hint=snippet_hint,
        )
        return items

    @staticmethod
    def _html_to_text(html: str) -> str:
        """BeautifulSoup으로 본문 텍스트만 추출"""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    async def _extract_from_text(
        self,
        text: str,
        url: str,
        context: str,
        keywords: Optional[list[str]] = None,
        title_hint: str = "",
        snippet_hint: str = "",
    ) -> list[VocItem]:
        """텍스트에서 LLM으로 VOC 추출.

        영어 프롬프트 사용 → 비한국어 페이지 추출 정확도 향상.
        native_vocab_hint로 시장별 리뷰 표현 인식 강화.
        """
        native_vocab_hint = ""
        if keywords:
            native_vocab_hint = f"Local review vocabulary hints: {', '.join(keywords[:8])}\n"

        title_ctx = f"Page title: {title_hint}\n" if title_hint else ""
        snippet_ctx = f"Search snippet: {snippet_hint}\n" if snippet_hint else ""

        prompt = f"""Extract consumer reviews/opinions (VOC) from the following webpage text.
Research context: {context}
{title_ctx}{snippet_ctx}{native_vocab_hint}
Rules:
- Extract ONLY actual consumer-written opinions (no summaries, ads, or generated content)
- Return empty array if no genuine consumer opinions found
- Include the original verbatim text for each opinion
- Detect language automatically; do NOT translate

Respond with a JSON array only (no other text):
[{{"original_text":"verbatim text","sentiment":"positive/negative/neutral","author":"author name or null","date":"date or null"}}]

Webpage text (first {WebReader.MAX_TEXT_CHARS} chars):
{text[:WebReader.MAX_TEXT_CHARS]}"""

        try:
            response = self.client.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            extracted = json.loads(response.text.strip())
        except Exception as e:
            logger.debug("[web_reader] LLM extract failed url=%s err=%s", url[:80], e)
            return []

        items: list[VocItem] = []
        for e in extracted:
            if not e.get("original_text"):
                continue
            item = VocItem(
                id=uuid.uuid4().hex[:12],
                project_id="",
                platform="web",
                sentiment=e.get("sentiment", "neutral"),
                original_text=e["original_text"],
                translated_text="",
                source_url=url,
                author=e.get("author"),
                date=e.get("date"),
                confidence=0.6,
                confidence_label="추정",
                collection_method="tier2_static",
            )
            items.append(item)

        return items
