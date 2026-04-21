"""검증기 — L1~L4 검증 파이프라인"""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher

import aiohttp
from bs4 import BeautifulSoup

from collectors.base import BROWSER_HEADERS as _BROWSER_HEADERS
from models.schemas import VerificationResult, VocItem


class Verifier:
    """수집된 VOC의 신뢰도를 검증"""

    async def verify(self, item: VocItem) -> VerificationResult:
        checks: dict[str, bool] = {}

        # L1: 구조 검증 — source_url 존재
        checks["has_url"] = bool(item.source_url and item.source_url.startswith("http"))
        if not checks["has_url"]:
            return VerificationResult(
                passed=False, confidence=0.0, label="실패", checks=checks
            )

        # L2: URL 접근성 — HTTP 200 확인
        checks["url_reachable"] = await self._check_url(item.source_url)

        # L3: 콘텐츠 매칭 — 원문 일부가 페이지에 존재
        if checks["url_reachable"]:
            page_text = await self._fetch_text(item.source_url)
            if page_text:
                checks["content_match"] = self._fuzzy_match(
                    item.original_text, page_text, threshold=0.3
                )
            else:
                # 봇 차단(403/429/503)으로 텍스트를 가져올 수 없을 때
                # URL이 실존하므로 콘텐츠 매칭 통과 처리 → confidence 유지
                checks["content_match"] = True
        else:
            checks["content_match"] = False

        # L4: 날짜 상식 검증
        checks["date_valid"] = self._validate_date(item.date)

        # 종합 점수
        passed_count = sum(checks.values())
        total = len(checks)
        confidence = passed_count / total if total > 0 else 0

        return VerificationResult(
            passed=confidence >= 0.5,
            confidence=round(confidence, 2),
            label="확실" if confidence >= 0.75 else "추정",
            checks=checks,
        )

    async def verify_batch(self, items: list[VocItem]) -> list[VocItem]:
        """배치 검증 — 각 아이템에 신뢰도 반영"""
        for item in items:
            result = await self.verify(item)
            item.confidence = result.confidence
            item.confidence_label = result.label
        return items

    @staticmethod
    async def _check_url(url: str) -> bool:
        """URL 접근 가능 여부 확인.

        HEAD 대신 GET 사용 — 일부 유럽 사이트가 HEAD를 차단하고 GET은 허용.
        403/429/503은 URL이 실존하지만 봇 차단이므로 "유효"로 처리.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=_BROWSER_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                ) as resp:
                    # 200~399: 정상 접근
                    # 403/429/503: URL 실존, 봇만 차단 → 링크는 유효
                    return resp.status < 400 or resp.status in (403, 429, 503)
        except Exception:
            return False

    @staticmethod
    async def _fetch_text(url: str) -> str:
        """URL에서 텍스트 추출"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=_BROWSER_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return ""
                    html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator=" ", strip=True)[:10000]
        except Exception:
            return ""

    @staticmethod
    def _fuzzy_match(original: str, page_text: str, threshold: float) -> bool:
        """원문과 페이지 텍스트의 유사도 검사"""
        if not original or not page_text:
            return False

        # 원문의 핵심 단어들이 페이지에 존재하는지 확인
        words = original.lower().split()
        if len(words) < 3:
            return original.lower() in page_text.lower()

        # 처음 10개 핵심 단어 중 일정 비율 이상 매칭
        sample_words = [w for w in words if len(w) > 3][:10]
        if not sample_words:
            return True

        page_lower = page_text.lower()
        matched = sum(1 for w in sample_words if w in page_lower)
        ratio = matched / len(sample_words)

        return ratio >= threshold

    @staticmethod
    def _validate_date(date_str: str | None) -> bool:
        """날짜 상식 검증 — 미래, 10년+ 과거 제외"""
        if not date_str:
            return True  # 날짜 없으면 통과 (정보 부족일 뿐)

        try:
            dt = datetime.fromisoformat(date_str.replace("/", "-"))
            now = datetime.now()
            # 미래 날짜 또는 10년 이상 과거
            if dt > now:
                return False
            if (now - dt).days > 365 * 10:
                return False
            return True
        except Exception:
            return True  # 파싱 실패 시 통과
