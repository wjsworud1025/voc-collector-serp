"""프리미엄 보고서 분석기 — 수집된 VOC에서 전략적 인사이트 추출"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import Counter

logger = logging.getLogger(__name__)

# 503/500 재시도 설정 (gemini-2.5-pro는 수요 급증에 더 민감)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 3.0   # 첫 재시도 대기(초), 이후 지수 증가

from google import genai

from agent.state import AgentContext
from models.schemas import (
    BrandLandscape,
    DeepDive,
    FormComparison,
    JourneyStage,
    KeywordDistribution,
    KpiCard,
    MarketingStrategy,
    Persona,
    ProductRecommendation,
    ReportAnalysis,
    SpotlightVoc,
    StrategicInsight,
    VocItem,
)


# 플랫폼별 참여도 가중치
_PLATFORM_WEIGHT = {"reddit": 3, "youtube": 2}


class Analyzer:
    """VOC 데이터 → ReportAnalysis 구조 생성"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)
        from config import GEMINI_ANALYSIS_MODEL
        self.model = GEMINI_ANALYSIS_MODEL

    async def analyze(self, ctx: AgentContext) -> ReportAnalysis:
        """전체 분석 파이프라인"""
        approved = [v for v in ctx.collected_items if v.approved]
        if not approved:
            # 승인 전이면 전체 사용 (루프 완료 직후 호출 시)
            approved = list(ctx.collected_items)

        # 1. 점수 계산
        scored = self._compute_scores(approved)

        # 2. 상위 30건을 LLM 분석 입력으로
        top_signal = sorted(scored, key=lambda v: -v.composite_score)[:30]

        # 3. LLM 단일 호출 → 전략 분석 JSON
        analysis = await self._generate_analysis(ctx, top_signal, approved)

        # 4. 키워드 분포 (코드 기반 집계)
        analysis.keyword_distributions = self._extract_keywords(approved)

        # 5. 스포트라이트 VOC 구성 (상위 5건)
        analysis.spotlight_vocs = self._build_spotlights(top_signal[:5])

        return analysis

    # ── 점수 계산 ────────────────────────────────────────────────

    def _compute_scores(self, items: list[VocItem]) -> list[VocItem]:
        for v in items:
            # quality: 텍스트 길이 + 구체성 (물음표/느낌표/숫자 포함 여부)
            text = v.original_text or ""
            length_score = min(60, len(text) // 10)
            specificity = sum([
                5 if any(c.isdigit() for c in text) else 0,
                5 if "?" in text or "!" in text else 0,
                5 if len(text) > 200 else 0,
            ])
            v.quality_score = min(100, 30 + length_score + specificity)

            # engagement: 플랫폼 가중 × confidence
            base = int((v.confidence or 0.5) * 100)
            weight = _PLATFORM_WEIGHT.get(v.platform, 1)
            v.engagement_score = base * weight

            # composite: 두 점수 합산을 0~10 정수로 압축 (순위용)
            v.composite_score = (v.quality_score + v.engagement_score) // 30

        return items

    # ── LLM 분석 ────────────────────────────────────────────────

    async def _generate_analysis(
        self,
        ctx: AgentContext,
        top_vocs: list[VocItem],
        all_vocs: list[VocItem],
    ) -> ReportAnalysis:
        plan = ctx.plan

        total = len(all_vocs)
        pos = sum(1 for v in all_vocs if v.sentiment == "positive")
        neg = sum(1 for v in all_vocs if v.sentiment == "negative")
        neu = total - pos - neg
        pos_pct = round(pos / total * 100) if total else 0
        neg_pct = round(neg / total * 100) if total else 0
        neu_pct = 100 - pos_pct - neg_pct

        voc_snippets = "\n".join(
            f"[{i+1}] [{v.sentiment}] [{v.platform}] {v.original_text[:300]}"
            for i, v in enumerate(top_vocs)
        )

        prompt = f"""당신은 글로벌 소비자 조사 전문가입니다.
다음 VOC 데이터를 분석하여 프리미엄 보고서용 전략 분석을 JSON으로 생성하세요.

시장: {plan.market}
제품 카테고리: {plan.product_category}
타겟 소비자: {plan.target_demographic}
총 VOC: {total}건 (긍정 {pos_pct}% / 부정 {neg_pct}% / 중립 {neu_pct}%)

상위 신호 VOC ({len(top_vocs)}건):
{voc_snippets}

다음 JSON 형식으로 응답하세요 (다른 텍스트 없이 JSON만):
{{
  "kpi_cards": [
    {{"title": "총 VOC 수집", "value": "{total}", "unit": "건", "trend_text": "", "trend_type": "neutral"}},
    {{"title": "긍정 비율", "value": "{pos_pct}", "unit": "%", "trend_text": "소비자 만족 신호", "trend_type": "up"}},
    {{"title": "부정 비율", "value": "{neg_pct}", "unit": "%", "trend_text": "개선 기회", "trend_type": "down"}},
    {{"title": "핵심 토픽 수", "value": "10", "unit": "개", "trend_text": "주요 관심사", "trend_type": "neutral"}}
  ],
  "paradigm_title": "시장 패러다임 변화를 나타내는 핵심 인사이트 제목 (1문장)",
  "paradigm_points": [
    "소비자 행동/기대에서 발견된 패러다임 변화 포인트 1",
    "패러다임 변화 포인트 2",
    "패러다임 변화 포인트 3"
  ],
  "audience_intro": "타겟 소비자층에 대한 간략한 설명 (1~2문장)",
  "personas": [
    {{
      "name": "페르소나 이름 (예: 품질 중시형 소비자)",
      "definition": "이 페르소나의 특성 정의 (1문장)",
      "behavior": "구매/사용 행동 패턴 (1~2문장)",
      "spotlight_quote": "VOC에서 발췌한 대표 인용구 (원문 그대로)",
      "spotlight_source": "출처 플랫폼"
    }},
    {{
      "name": "페르소나 이름 2",
      "definition": "정의",
      "behavior": "행동 패턴",
      "spotlight_quote": "대표 인용구",
      "spotlight_source": "출처 플랫폼"
    }},
    {{
      "name": "페르소나 이름 3",
      "definition": "정의",
      "behavior": "행동 패턴",
      "spotlight_quote": "대표 인용구",
      "spotlight_source": "출처 플랫폼"
    }}
  ],
  "journey_intro": "구매 여정 분석 요약 (1~2문장)",
  "journey_stages": [
    {{"stage": "인지", "emotion": "호기심/필요 인식", "trigger": "트리거 요인", "behavior": "행동 패턴", "opportunity": "마케팅 기회"}},
    {{"stage": "탐색", "emotion": "비교/고민", "trigger": "트리거 요인", "behavior": "행동 패턴", "opportunity": "마케팅 기회"}},
    {{"stage": "구매", "emotion": "결정/기대", "trigger": "트리거 요인", "behavior": "행동 패턴", "opportunity": "마케팅 기회"}},
    {{"stage": "사용", "emotion": "만족/실망", "trigger": "트리거 요인", "behavior": "행동 패턴", "opportunity": "마케팅 기회"}},
    {{"stage": "공유", "emotion": "지지/비판", "trigger": "트리거 요인", "behavior": "행동 패턴", "opportunity": "마케팅 기회"}}
  ],
  "form_comparisons": [
    {{
      "form_name": "제품 유형/형태 이름 1",
      "form_subtitle": "부제",
      "products": "대표 제품명 예시",
      "pros_title": "주요 장점 요약",
      "pros_detail": "장점 세부 설명",
      "cons_title": "주요 단점 요약",
      "cons_detail": "단점 세부 설명",
      "representative_voc": "대표 VOC 원문 발췌",
      "badge_color": "success"
    }},
    {{
      "form_name": "제품 유형/형태 이름 2",
      "form_subtitle": "부제",
      "products": "대표 제품명 예시",
      "pros_title": "주요 장점 요약",
      "pros_detail": "장점 세부 설명",
      "cons_title": "주요 단점 요약",
      "cons_detail": "단점 세부 설명",
      "representative_voc": "대표 VOC 원문 발췌",
      "badge_color": "warning"
    }}
  ],
  "brand_landscape": [
    {{"brand": "브랜드명 1", "description": "소비자 인식 특성"}},
    {{"brand": "브랜드명 2", "description": "소비자 인식 특성"}}
  ],
  "deep_dives": [
    {{"title": "심층 분석 주제 1", "body": "상세 분석 내용 (2~3문장)"}},
    {{"title": "심층 분석 주제 2", "body": "상세 분석 내용 (2~3문장)"}}
  ],
  "spotlight_intro": "하이시그널 VOC 스포트라이트 설명 (1문장)",
  "strategic_insights": [
    {{"number": 1, "title": "전략적 인사이트 제목", "impact": "비즈니스 임팩트 설명 (1~2문장)", "priority": "critical"}},
    {{"number": 2, "title": "전략적 인사이트 제목 2", "impact": "비즈니스 임팩트 설명", "priority": "high"}},
    {{"number": 3, "title": "전략적 인사이트 제목 3", "impact": "비즈니스 임팩트 설명", "priority": "high"}},
    {{"number": 4, "title": "전략적 인사이트 제목 4", "impact": "비즈니스 임팩트 설명", "priority": "mid"}},
    {{"number": 5, "title": "전략적 인사이트 제목 5", "impact": "비즈니스 임팩트 설명", "priority": "mid"}}
  ],
  "marketing_strategies": [
    {{"perspective": "마케팅 관점 1", "old_approach": "기존 접근법", "new_approach": "새로운 접근법", "priority": "high"}},
    {{"perspective": "마케팅 관점 2", "old_approach": "기존 접근법", "new_approach": "새로운 접근법", "priority": "high"}},
    {{"perspective": "마케팅 관점 3", "old_approach": "기존 접근법", "new_approach": "새로운 접근법", "priority": "mid"}}
  ],
  "product_recommendations": [
    {{"label": "단기 (0~3개월)", "title": "제품 개발 방향 제목", "body": "구체적 실행 방향 (2~3문장)"}},
    {{"label": "중기 (3~6개월)", "title": "제품 개발 방향 제목 2", "body": "구체적 실행 방향"}},
    {{"label": "장기 (6~12개월)", "title": "제품 개발 방향 제목 3", "body": "구체적 실행 방향"}}
  ]
}}

중요:
- 모든 분석은 실제 수집된 VOC 데이터에 기반해야 합니다
- 한국어로 작성 (원문 인용은 원어 유지)
- persona spotlight_quote는 위 VOC 원문에서 직접 발췌
- brand_landscape는 VOC에 실제로 언급된 브랜드만 포함 (없으면 빈 배열)
- form_comparisons는 실제 VOC에서 구별되는 제품 형태/유형이 있을 때만 2~3개"""

        # 503/500 재시도 (지수 백오프)
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                    },
                )
                break  # 성공
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                is_overload = any(
                    code in err_str for code in ("503", "500", "overloaded", "UNAVAILABLE")
                )
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))  # 3s → 6s → 12s
                    logger.warning(
                        "Analyzer generate_content %s — attempt %d/%d, retry in %.1fs. Error: %s",
                        "overload" if is_overload else "failed",
                        attempt, _MAX_RETRIES, delay, err_str[:120],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Analyzer permanently failed after %d attempts. Last error: %s",
                        _MAX_RETRIES, err_str[:200],
                    )
                    raise
        else:
            # for-else: break 없이 루프 종료 (전부 실패) — 위 raise로 도달 불가지만 안전장치
            raise last_exc  # type: ignore[misc]

        raw = response.text.strip()
        data = json.loads(raw)

        # Pydantic 모델로 변환
        return ReportAnalysis(
            project_id=ctx.plan.market,  # temp, overwritten by caller
            market=plan.market,
            product_category=plan.product_category,
            target_audience=plan.target_demographic,
            kpi_cards=[KpiCard(**k) for k in data.get("kpi_cards", [])],
            paradigm_title=data.get("paradigm_title", ""),
            paradigm_points=data.get("paradigm_points", []),
            audience_intro=data.get("audience_intro", ""),
            personas=[Persona(**p) for p in data.get("personas", [])],
            journey_intro=data.get("journey_intro", ""),
            journey_stages=[JourneyStage(**j) for j in data.get("journey_stages", [])],
            form_comparisons=[FormComparison(**f) for f in data.get("form_comparisons", [])],
            brand_landscape=[BrandLandscape(**b) for b in data.get("brand_landscape", [])],
            deep_dives=[DeepDive(**d) for d in data.get("deep_dives", [])],
            spotlight_intro=data.get("spotlight_intro", ""),
            strategic_insights=[StrategicInsight(**s) for s in data.get("strategic_insights", [])],
            marketing_strategies=[MarketingStrategy(**m) for m in data.get("marketing_strategies", [])],
            product_recommendations=[ProductRecommendation(**r) for r in data.get("product_recommendations", [])],
        )

    # ── 키워드 분포 ──────────────────────────────────────────────

    def _extract_keywords(self, items: list[VocItem]) -> list[KeywordDistribution]:
        """topics 필드에서 키워드 빈도 집계 후 상위 20개 반환"""
        freq: Counter = Counter()
        sentiment_map: dict[str, Counter] = {}

        for v in items:
            for t in (v.topics or []):
                t = t.strip().lower()
                if not t:
                    continue
                freq[t] += 1
                if t not in sentiment_map:
                    sentiment_map[t] = Counter()
                sentiment_map[t][v.sentiment] += 1

        if not freq:
            return []

        top = freq.most_common(20)
        max_count = top[0][1] if top else 1
        total_vocs = len(items)

        # 색상 팔레트 (긍정=초록, 부정=빨강, 중립=회색)
        colors_by_emotion = {
            "긍정": "#10b981",
            "부정": "#ef4444",
            "중립": "#6b7280",
        }

        result = []
        for rank, (kw, cnt) in enumerate(top, 1):
            pct = round(cnt / total_vocs * 100, 1) if total_vocs else 0
            bar_w = max(5, int(cnt / max_count * 100))

            # 주요 감성 결정
            sm = sentiment_map.get(kw, Counter())
            if sm:
                dominant = sm.most_common(1)[0][0]
                emotion_tag = {"positive": "긍정", "negative": "부정", "neutral": "중립"}.get(dominant, "중립")
            else:
                emotion_tag = "중립"

            result.append(KeywordDistribution(
                rank=rank,
                keyword=kw,
                count=cnt,
                percentage=pct,
                bar_width_percent=bar_w,
                bar_color=colors_by_emotion[emotion_tag],
                emotion_tag=emotion_tag,
            ))

        return result

    # ── 스포트라이트 VOC ─────────────────────────────────────────

    def _build_spotlights(self, top_items: list[VocItem]) -> list[SpotlightVoc]:
        result = []
        for v in top_items:
            spotlight_type = {
                "positive": "default",
                "neutral": "warning",
                "negative": "negative",
            }.get(v.sentiment, "default")

            excerpt = v.translated_text[:200] if v.translated_text else v.original_text[:200]
            if len(v.translated_text or v.original_text) > 200:
                excerpt += "..."

            result.append(SpotlightVoc(
                voc_id=v.id,
                title_text=_make_title(v),
                source=v.platform.capitalize(),
                score_total=v.composite_score,
                score_quality=v.quality_score,
                score_engagement=v.engagement_score,
                excerpt=excerpt,
                url=v.source_url or "",
                spotlight_type=spotlight_type,
            ))
        return result


def _make_title(v: VocItem) -> str:
    """VOC에서 짧은 제목 생성 (첫 문장 또는 첫 50자)"""
    text = v.translated_text or v.original_text or ""
    # 첫 문장 분리
    for sep in [".", "!", "?", "\n"]:
        idx = text.find(sep)
        if 10 <= idx <= 80:
            return text[:idx + 1].strip()
    return text[:60].strip() + ("..." if len(text) > 60 else "")
