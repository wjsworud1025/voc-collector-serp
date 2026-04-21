"""Google Custom Search API 수집기"""

from __future__ import annotations

import json
import os
import uuid

import aiohttp
from bs4 import BeautifulSoup

from collectors.base import BaseCollector
from models.schemas import VocItem
from google import genai


class GoogleSearchCollector(BaseCollector):
    """Google CSE로 검색 → 페이지 읽기 → LLM VOC 추출"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_CSE_API_KEY", "")
        self.cx = os.getenv("GOOGLE_CSE_CX", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=self.gemini_key)
        from config import GEMINI_MODEL
        self._gemini_model = GEMINI_MODEL

    async def collect(
        self,
        query: str,
        context: str,
        max_results: int = 10,
        keywords: list[str] | None = None,
        gl: str | None = None,
        lr: str | None = None,
    ) -> list[VocItem]:
        # 1. Google CSE 검색
        urls = await self._search(query, max_results, gl=gl, lr=lr)
        if not urls:
            return []

        # 2. 각 URL에서 페이지 읽기 + VOC 추출
        items: list[VocItem] = []
        async with aiohttp.ClientSession() as session:
            for url, title, snippet in urls:
                try:
                    page_items = await self._extract_from_url(
                        session, url, title, snippet, context, keywords or []
                    )
                    items.extend(page_items)
                except Exception:
                    continue

        return items

    async def _search(
        self,
        query: str,
        max_results: int,
        gl: str | None = None,
        lr: str | None = None,
    ) -> list[tuple[str, str, str]]:
        """Google CSE API 호출 → (url, title, snippet) 목록

        gl: 국가 코드 (예: "de", "fr") — 해당 국가 결과를 우선 노출
        lr: 언어 제한 (예: "lang_de", "lang_fr") — 해당 언어 페이지만 반환
        """
        if not self.api_key or not self.cx:
            return []

        results = []
        async with aiohttp.ClientSession() as session:
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": min(max_results, 10),
            }
            if gl:
                params["gl"] = gl
            if lr:
                params["lr"] = lr
            async with session.get(
                "https://www.googleapis.com/customsearch/v1", params=params
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    err = data.get("error", {})
                    reason = err.get("details", [{}])[0].get("reason", "") if err.get("details") else ""
                    msg = err.get("message", f"HTTP {resp.status}")
                    if reason == "API_KEY_SERVICE_BLOCKED":
                        raise RuntimeError(
                            "Google Custom Search API가 비활성화 상태입니다. "
                            "설정 → Google 검색 API 키 발급 방법을 참고해 활성화하세요."
                        )
                    raise RuntimeError(f"Google CSE API 오류: {msg}")

            for item in data.get("items", []):
                results.append((
                    item.get("link", ""),
                    item.get("title", ""),
                    item.get("snippet", ""),
                ))

        return results

    async def _extract_from_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        title: str,
        snippet: str,
        context: str,
        keywords: list[str],
    ) -> list[VocItem]:
        """URL에서 페이지 읽기 → LLM으로 VOC 추출"""

        # 페이지 fetch
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []

        # BS4로 본문 추출
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        if len(text) < 100:
            return []

        # ── 사전 필터: 키워드 미포함 페이지는 LLM 호출 없이 skip ──
        if keywords:
            text_lower = text.lower()
            matched = sum(1 for kw in keywords if kw.lower() in text_lower)
            if matched == 0:
                return []  # 키워드 0개 매칭 → 무관 페이지

        # LLM으로 VOC 추출 — 관련성 필터링 강화
        kw_hint = ""
        if keywords:
            kw_hint = (
                f"\n\n**필수 매칭 키워드 (이 중 하나 이상이 원문에 포함되어야 함):**\n"
                f"{', '.join(keywords[:10])}"
            )

        prompt = f"""다음 웹페이지에서 **조사 주제와 직접 관련된** 소비자 의견(VOC)만 추출하세요.

조사 주제: {context}{kw_hint}

**엄격한 규칙:**
- 조사 주제의 제품/서비스에 **직접적으로** 언급하는 의견만 추출
- 위 키워드 중 하나 이상이 원문에 명시되어야 함
- 관련 없는 제품, 일반적인 의견, 다른 카테고리 의견은 **절대 포함하지 마세요**
- 마케팅 문구, 제품 설명, 기사 본문은 제외
- 실제 소비자/사용자가 작성한 경험담, 리뷰, 불만, 추천만 포함
- 관련 VOC가 없으면 반드시 빈 배열 [] 반환
- 관련성이 애매한 의견은 제외 (포함보다 제외가 낫습니다)

**중요: original_text는 페이지의 원문을 그대로 복사. 번역·요약·수정 절대 금지.**

JSON 배열로 응답:
[{{"original_text":"원문","sentiment":"positive/negative/neutral","author":"작성자 또는 null","date":"날짜 또는 null"}}]

페이지 제목: {title}
텍스트 (처음 6000자):
{text[:6000]}"""

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
        except Exception:
            return []

        items = []
        for e in extracted:
            original = e.get("original_text", "")
            if not original:
                continue
            # ── 추출 후 키워드 매칭 재확인 (LLM hallucination 방어) ──
            if keywords:
                orig_lower = original.lower()
                if not any(kw.lower() in orig_lower for kw in keywords):
                    continue
            item = VocItem(
                id=uuid.uuid4().hex[:12],
                project_id="",
                platform="google",
                sentiment=e.get("sentiment", "neutral"),
                original_text=original,
                translated_text="",
                source_url=url,
                author=e.get("author"),
                date=e.get("date"),
                confidence=0.7,
                confidence_label="추정",
                collection_method="tier2_static",
            )
            items.append(item)

        return items
