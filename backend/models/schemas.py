"""Pydantic 모델 — VOC Collector 데이터 스키마"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── 에이전트 상태 ─────────────────────────────────────────────

class AgentState(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REPLANNING = "replanning"
    SYNTHESIZING = "synthesizing"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


# ── 조사계획 ──────────────────────────────────────────────────

class SearchTask(BaseModel):
    """조사계획 내 개별 검색 태스크"""
    id: str
    source: str                    # "google", "reddit"
    query: str                     # 검색 쿼리
    language: str = "en"
    max_results: int = 10
    completed: bool = False
    results_count: int = 0


class ResearchPlan(BaseModel):
    """LLM이 생성한 조사계획"""
    market: str                    # "미국", "유럽"
    product_category: str          # "제빙기", "냉장고"
    target_demographic: str        # "MZ세대", "주부"
    keywords: list[str]            # ["ice maker", "nugget ice"]
    languages: list[str]           # ["en"]
    platforms: list[str]           # ["google", "reddit"]
    tasks: list[SearchTask]
    estimated_total: int = 30


class PlanRevision(BaseModel):
    """조사계획 수정 이력"""
    iteration: int
    reason: str                    # "부정 리뷰 부족", "유럽 데이터 부족"
    added_tasks: list[SearchTask]
    removed_task_ids: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


# ── VOC 아이템 ────────────────────────────────────────────────

class VerificationResult(BaseModel):
    """검증 결과"""
    passed: bool
    confidence: float              # 0.0 ~ 1.0
    label: str                     # "확실" / "추정"
    checks: dict[str, bool]        # {"has_url": True, "url_reachable": True, ...}


class VocItem(BaseModel):
    """수집된 VOC 단건"""
    id: str
    project_id: str
    platform: str                  # "reddit", "google", "web"
    sentiment: str                 # "positive" / "negative" / "neutral"
    original_text: str
    translated_text: str           # 한국어 번역
    source_url: str
    author: str | None = None
    date: str | None = None
    topics: list[str] = []
    content_hash: str = ""
    confidence: float = 0.0
    confidence_label: str = "추정"
    collection_method: str = "tier2_static"
    approved: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    # 프리미엄 보고서용 점수 필드
    quality_score: int = 0         # 텍스트 품질 점수 (0~100)
    engagement_score: int = 0      # 플랫폼 가중 참여도 점수
    composite_score: int = 0       # quality + engagement 합산 순위 점수

    def compute_hash(self) -> str:
        """원문 기반 SHA256 해시 (중복 방지)"""
        normalized = self.original_text.strip().lower()
        self.content_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return self.content_hash


# ── 에이전트 이벤트 (SSE) ─────────────────────────────────────

class AgentEvent(BaseModel):
    """SSE로 프론트엔드에 전달되는 이벤트"""
    type: str                      # "plan_created", "item_found", "evaluated", ...
    message: str = ""
    data: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_sse(self) -> str:
        payload = self.model_dump(mode="json")
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── 평가 결과 ─────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    """에이전트 루프 평가 결과"""
    sufficient: bool
    total_collected: int
    total_verified: int
    duplicates_removed: int
    gaps: list[str]                # ["부정 리뷰 1건뿐", "유럽 데이터 없음"]
    sentiment_dist: dict[str, int] = {}  # {"positive": 12, "negative": 3, "neutral": 5}


# ── API 요청/응답 ─────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    user_request: str              # 사용자 자연어 요청


class ProjectResponse(BaseModel):
    id: str
    name: str
    user_request: str
    status: str
    created_at: str
    voc_count: int = 0


class SettingsUpdate(BaseModel):
    key: str
    value: str


# ── 프리미엄 보고서 분석 스키마 ────────────────────────────────

class KpiCard(BaseModel):
    title: str
    value: str
    unit: str = ""
    trend_text: str = ""
    trend_type: str = "neutral"   # "up", "down", "neutral"


class Persona(BaseModel):
    name: str
    definition: str
    behavior: str
    spotlight_quote: str = ""
    spotlight_source: str = ""
    spotlight_url: str = ""


class JourneyStage(BaseModel):
    stage: str
    emotion: str
    trigger: str
    behavior: str
    opportunity: str


class FormComparison(BaseModel):
    form_name: str
    form_subtitle: str
    products: str
    pros_title: str
    pros_detail: str
    cons_title: str
    cons_detail: str
    representative_voc: str
    badge_color: str = "warning"  # "success", "warning", "danger"


class BrandLandscape(BaseModel):
    brand: str
    description: str


class DeepDive(BaseModel):
    title: str
    body: str


class SpotlightVoc(BaseModel):
    voc_id: str
    title_text: str
    source: str
    score_total: int
    score_quality: int
    score_engagement: int
    excerpt: str
    url: str
    spotlight_type: str = "default"   # "default", "warning", "negative"


class StrategicInsight(BaseModel):
    number: int
    title: str
    impact: str
    priority: str = "mid"    # "critical", "high", "mid"


class MarketingStrategy(BaseModel):
    perspective: str
    old_approach: str
    new_approach: str
    priority: str = "high"   # "high", "mid"


class ProductRecommendation(BaseModel):
    label: str
    title: str
    body: str


class KeywordDistribution(BaseModel):
    rank: int
    keyword: str
    count: int
    percentage: float
    bar_width_percent: int
    bar_color: str           # hex color string
    emotion_tag: str         # "긍정", "부정", "중립"


class ReportAnalysis(BaseModel):
    """프리미엄 보고서 전체 분석 결과"""
    project_id: str
    market: str
    product_category: str
    target_audience: str
    # Page 1: KPI 대시보드
    kpi_cards: list[KpiCard] = []
    # Page 2: 시장 패러다임
    paradigm_title: str = ""
    paradigm_points: list[str] = []
    # Page 3: 구매자 페르소나
    audience_intro: str = ""
    personas: list[Persona] = []
    # Page 4: 구매 여정
    journey_intro: str = ""
    journey_stages: list[JourneyStage] = []
    # Page 5: 제형 비교
    form_comparisons: list[FormComparison] = []
    brand_landscape: list[BrandLandscape] = []
    deep_dives: list[DeepDive] = []
    # Page 6: 하이시그널 VOC 스포트라이트
    spotlight_intro: str = ""
    spotlight_vocs: list[SpotlightVoc] = []
    # Page 7: 전략적 인사이트
    strategic_insights: list[StrategicInsight] = []
    # Page 8: 마케팅 전략 전환
    marketing_strategies: list[MarketingStrategy] = []
    # Page 9: 제품 개발 방향
    product_recommendations: list[ProductRecommendation] = []
    # Appendix 1: 키워드 분포
    keyword_distributions: list[KeywordDistribution] = []
    generated_at: datetime = Field(default_factory=datetime.now)
