"""SerpApi Google search 응답 Pydantic 모델 — 응답 변형 케이스 안전 파싱.

목적:
- SerpApi의 organic_results 외 모든 필드를 안전하게 파싱
- link/redirect_link, snippet/rich_snippet 등 변형 케이스 자동 폴백
- ConfigDict(extra="allow")로 SerpApi 신규 필드 추가에도 안전
- best_link/best_snippet 프로퍼티로 호출 측 코드 단순화
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class SerpApiSearchMetadata(BaseModel):
    """SerpApi 응답의 search_metadata 블록."""
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    status: Optional[str] = None  # "Success" | "Error" | "Cached"
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    google_url: Optional[str] = None
    raw_html_file: Optional[str] = None
    total_time_taken: Optional[float] = None


class SerpApiRichSnippet(BaseModel):
    """rich_snippet 블록 — 별점/가격/리뷰수 등 구조화 데이터."""
    model_config = ConfigDict(extra="allow")

    top: Optional[dict] = None
    bottom: Optional[dict] = None
    detected_extensions: Optional[dict] = None


class SerpApiSitelinks(BaseModel):
    """sitelinks 블록 — inline / expanded 서브 링크."""
    model_config = ConfigDict(extra="allow")

    inline: list[dict] = Field(default_factory=list)
    expanded: list[dict] = Field(default_factory=list)


class SerpApiOrganicResult(BaseModel):
    """조직 검색 결과 단일 항목 — 모든 변형 필드 허용."""
    model_config = ConfigDict(extra="allow")

    position: Optional[int] = None
    title: Optional[str] = None
    link: Optional[str] = None
    redirect_link: Optional[str] = None
    displayed_link: Optional[str] = None
    source: Optional[str] = None
    snippet: Optional[str] = None
    snippet_highlighted_words: list[str] = Field(default_factory=list)
    sitelinks: Optional[SerpApiSitelinks] = None
    rich_snippet: Optional[SerpApiRichSnippet] = None
    about_this_result: Optional[dict] = None
    date: Optional[str] = None
    cached_page_link: Optional[str] = None
    related_pages_link: Optional[str] = None

    @property
    def best_link(self) -> str:
        """`link` 우선, 없으면 `redirect_link`, 그것도 없으면 빈 문자열."""
        return self.link or self.redirect_link or ""

    @property
    def best_snippet(self) -> str:
        """`snippet` + rich_snippet.top.extensions(별점 등)을 조합."""
        parts: list[str] = []
        if self.snippet:
            parts.append(self.snippet)
        if self.rich_snippet and self.rich_snippet.top:
            ext = self.rich_snippet.top.get("extensions", [])
            if ext:
                parts.append(" | ".join(str(e) for e in ext))
        return " ".join(p for p in parts if p).strip()


class SerpApiResponse(BaseModel):
    """SerpApi Google 검색 전체 응답."""
    model_config = ConfigDict(extra="allow")

    search_metadata: Optional[SerpApiSearchMetadata] = None
    search_parameters: Optional[dict] = None
    search_information: Optional[dict] = None
    organic_results: list[SerpApiOrganicResult] = Field(default_factory=list)
    ads: list[dict] = Field(default_factory=list)
    related_searches: list[dict] = Field(default_factory=list)
    pagination: Optional[dict] = None
    knowledge_graph: Optional[dict] = None
    error: Optional[str] = None

    def is_success(self) -> bool:
        """error 없고 organic_results 1건 이상이면 성공."""
        return self.error is None and len(self.organic_results) > 0

    def to_url_tuples(self) -> list[tuple[str, str, str]]:
        """(url, title, snippet) 튜플 목록 — 기존 collector 인터페이스 호환."""
        out: list[tuple[str, str, str]] = []
        for r in self.organic_results:
            url = r.best_link
            if url:
                out.append((url, r.title or "", r.best_snippet))
        return out


def parse_serpapi_response(raw: dict) -> SerpApiResponse:
    """raw dict → 검증된 Pydantic 모델.

    SerpApi 응답 스키마 변경에 대비한 폴백:
    - 전체 파싱 실패 시 organic_results만이라도 부분 파싱
    - 알 수 없는 필드는 extra="allow"로 자동 무시
    """
    if not isinstance(raw, dict):
        return SerpApiResponse(error=f"Invalid response type: {type(raw).__name__}")

    try:
        return SerpApiResponse(**raw)
    except Exception as e:
        logger.warning(
            "SerpApi response parse failed: %s; raw keys=%s", e, list(raw.keys())
        )
        # 부분 파싱 폴백 — organic_results만이라도 건지기
        partial: list[SerpApiOrganicResult] = []
        for r in raw.get("organic_results", []):
            if isinstance(r, dict):
                try:
                    partial.append(SerpApiOrganicResult(**r))
                except Exception:
                    continue
        return SerpApiResponse(
            organic_results=partial,
            error=f"Partial parse: {e}",
        )
