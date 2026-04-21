"""에이전트 상태 관리"""

from __future__ import annotations

from models.schemas import (
    AgentState,
    EvaluationResult,
    PlanRevision,
    ResearchPlan,
    VocItem,
)


class AgentContext:
    """에이전트의 누적 작업 상태 — 매 반복마다 갱신"""

    def __init__(self):
        self.state: AgentState = AgentState.PLANNING
        self.iteration: int = 0
        self.plan: ResearchPlan | None = None
        self.plan_history: list[PlanRevision] = []
        self.collected_items: list[VocItem] = []
        self.rejected_items: list[dict] = []  # {"item": ..., "reason": ...}
        self.dedup_count: int = 0

    @property
    def verified_count(self) -> int:
        return len([i for i in self.collected_items if i.confidence >= 0.5])

    @property
    def sentiment_dist(self) -> dict[str, int]:
        dist: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}
        for item in self.collected_items:
            if item.sentiment in dist:
                dist[item.sentiment] += 1
        return dist

    def add_item(self, item: VocItem) -> bool:
        """VOC 추가 (중복 시 False 반환)"""
        existing_hashes = {i.content_hash for i in self.collected_items}
        if item.content_hash and item.content_hash in existing_hashes:
            self.dedup_count += 1
            return False
        self.collected_items.append(item)
        return True
