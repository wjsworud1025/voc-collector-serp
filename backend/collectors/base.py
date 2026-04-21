"""수집기 추상 베이스 클래스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.schemas import VocItem

# 유럽 e커머스(Amazon.de, Idealo, Trustpilot 등)는 봇 요청 차단 → 브라우저 헤더 필요
# Accept-Language에 유럽 언어 포함 → 현지화 콘텐츠 협상 개선
BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8,fr;q=0.7,it;q=0.6,es;q=0.5",
}


class BaseCollector(ABC):
    """모든 수집기의 베이스"""

    @abstractmethod
    async def collect(
        self,
        query: str,
        context: str,
        max_results: int = 10,
        keywords: list[str] | None = None,
    ) -> list[VocItem]:
        """쿼리 기반 VOC 수집

        keywords: 사전 필터링용 키워드 (제품명, 카테고리). 페이지 텍스트에
        이 키워드 중 하나라도 포함되어야 추출 단계로 진입.
        """
        ...
