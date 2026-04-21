"""수집 결과 평가 — 충분성 판단 + 갭 분석"""

from __future__ import annotations

from agent.state import AgentContext
from models.schemas import EvaluationResult


class Evaluator:
    """수집된 VOC를 평가하고 부족분을 식별"""

    MIN_TOTAL = 10          # 최소 수집 건수 (관련 VOC 기준)
    MIN_NEGATIVE_RATIO = 0.1  # 부정 리뷰 최소 비율
    MIN_RELEVANCE_RATIO = 0.5  # 관련성 최소 비율

    async def evaluate(self, ctx: AgentContext) -> EvaluationResult:
        total = len(ctx.collected_items)
        verified = ctx.verified_count
        dist = ctx.sentiment_dist

        # 관련 VOC만 카운트 (approved=True)
        relevant_count = sum(1 for item in ctx.collected_items if item.approved)
        # Fallback: synthesizer가 아직 실행되지 않은 경우 verified_count 사용
        if relevant_count == 0 and ctx.verified_count > 0:
            relevant_count = ctx.verified_count

        gaps: list[str] = []

        # 1. 관련 VOC 절대량 부족
        if relevant_count < self.MIN_TOTAL:
            gaps.append(
                f"관련 VOC 부족 (현재 {relevant_count}건, 최소 {self.MIN_TOTAL}건 필요)"
            )

        # 2. 관련성 비율 체크 — 비관련 VOC가 너무 많으면 쿼리 품질 문제
        if total > 5:
            relevance_ratio = relevant_count / total
            if relevance_ratio < self.MIN_RELEVANCE_RATIO:
                gaps.append(
                    f"관련성 낮음 ({relevant_count}/{total}건, "
                    f"{relevance_ratio:.0%}) — 검색 쿼리를 더 구체적으로 변경 필요"
                )

        # 3. 감성 편향 체크 (관련 VOC 기준)
        if relevant_count > 0:
            neg_ratio = dist.get("negative", 0) / relevant_count
            if neg_ratio < self.MIN_NEGATIVE_RATIO and relevant_count >= 5:
                gaps.append(
                    f"부정 리뷰 부족 (현재 {dist.get('negative', 0)}건, "
                    f"비율 {neg_ratio:.0%})"
                )

            pos_ratio = dist.get("positive", 0) / relevant_count
            if pos_ratio < self.MIN_NEGATIVE_RATIO and relevant_count >= 5:
                gaps.append(
                    f"긍정 리뷰 부족 (현재 {dist.get('positive', 0)}건)"
                )

        # 4. 검증률 체크
        if total > 0 and verified / total < 0.5:
            gaps.append(
                f"검증 통과율 낮음 ({verified}/{total}, "
                f"{verified / total:.0%})"
            )

        sufficient = len(gaps) == 0

        return EvaluationResult(
            sufficient=sufficient,
            total_collected=total,
            total_verified=verified,
            duplicates_removed=ctx.dedup_count,
            gaps=gaps,
            sentiment_dist=dist,
        )
