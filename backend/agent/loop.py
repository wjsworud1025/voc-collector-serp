"""에이전트 메인 루프 — plan → execute → evaluate → replan"""

from __future__ import annotations

import json
from typing import AsyncGenerator

from agent.analyzer import Analyzer
from agent.evaluator import Evaluator
from agent.executor import Executor
from agent.planner import Planner
from agent.state import AgentContext
from agent.synthesizer import Synthesizer
from models.database import get_db
from models.schemas import AgentEvent, AgentState


class ResearchAgent:
    """VOC 수집 에이전트 — 자율 탐색 루프"""

    MAX_ITERATIONS = 5

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.planner = Planner()
        self.executor = Executor(project_id)
        self.evaluator = Evaluator()
        self.synthesizer = Synthesizer()
        self.analyzer = Analyzer()

    async def run(self, user_request: str) -> AsyncGenerator[AgentEvent, None]:
        ctx = AgentContext()

        # ── 프로젝트 상태 업데이트 ──
        await self._update_project_status("running")

        # ── 1. 조사계획 수립 ──
        ctx.state = AgentState.PLANNING
        yield AgentEvent(
            type="state_change",
            message="조사계획 수립 중...",
            data={"state": "planning"},
        )

        try:
            ctx.plan = await self.planner.create(user_request)
        except Exception as e:
            yield AgentEvent(type="error", message=f"조사계획 수립 실패: {e}")
            await self._update_project_status("failed")
            return

        yield AgentEvent(
            type="plan_created",
            message="조사계획 수립 완료",
            data={
                "market": ctx.plan.market,
                "product": ctx.plan.product_category,
                "keywords": ctx.plan.keywords,
                "platforms": ctx.plan.platforms,
                "task_count": len(ctx.plan.tasks),
                "estimated_total": ctx.plan.estimated_total,
            },
        )

        # ── 2. 에이전트 루프 ──
        for i in range(self.MAX_ITERATIONS):
            ctx.iteration = i + 1
            ctx.state = AgentState.EXECUTING

            yield AgentEvent(
                type="iteration_start",
                message=f"탐색 반복 {ctx.iteration}/{self.MAX_ITERATIONS}",
                data={"iteration": ctx.iteration},
            )

            # 각 태스크 순차 실행
            for task in ctx.plan.tasks:
                if task.completed:
                    continue
                async for event in self.executor.run(task, ctx):
                    yield event

            # 진행 상황 요약
            yield AgentEvent(
                type="progress",
                message=f"수집 {len(ctx.collected_items)}건, 중복제거 {ctx.dedup_count}건",
                data={
                    "collected": len(ctx.collected_items),
                    "verified": ctx.verified_count,
                    "dedup": ctx.dedup_count,
                    "sentiment": ctx.sentiment_dist,
                },
            )

            # ── 3. 평가 ──
            ctx.state = AgentState.EVALUATING
            yield AgentEvent(
                type="state_change",
                message="수집 결과 평가 중...",
                data={"state": "evaluating"},
            )

            eval_result = await self.evaluator.evaluate(ctx)
            await self._log_agent_run(ctx, eval_result)

            yield AgentEvent(
                type="evaluated",
                message="평가 완료" if eval_result.sufficient else "부족분 발견",
                data={
                    "sufficient": eval_result.sufficient,
                    "gaps": eval_result.gaps,
                    "total": eval_result.total_collected,
                    "verified": eval_result.total_verified,
                },
            )

            if eval_result.sufficient:
                break

            # ── 4. 재계획 ──
            if ctx.iteration < self.MAX_ITERATIONS:
                ctx.state = AgentState.REPLANNING
                yield AgentEvent(
                    type="state_change",
                    message="추가 탐색 계획 수립 중...",
                    data={"state": "replanning", "gaps": eval_result.gaps},
                )

                try:
                    revision = await self.planner.revise(ctx, eval_result.gaps)
                    ctx.plan_history.append(revision)

                    yield AgentEvent(
                        type="plan_revised",
                        message=f"계획 수정: {revision.reason}",
                        data={
                            "reason": revision.reason,
                            "added_tasks": [
                                {"source": t.source, "query": t.query}
                                for t in revision.added_tasks
                            ],
                            "iteration": ctx.iteration,
                        },
                    )
                except Exception as e:
                    yield AgentEvent(
                        type="replan_error",
                        message=f"재계획 실패: {e}",
                    )

        # ── 5. 최종 구조화 ──
        ctx.state = AgentState.SYNTHESIZING
        yield AgentEvent(
            type="state_change",
            message="최종 분석 및 구조화 중...",
            data={"state": "synthesizing"},
        )

        result = await self.synthesizer.run(ctx)

        # DB에 VOC 저장
        await self._save_items(ctx)

        # ── 6. 프리미엄 분석 (백그라운드) ──
        try:
            yield AgentEvent(
                type="state_change",
                message="프리미엄 분석 생성 중...",
                data={"state": "analyzing"},
            )
            analysis = await self.analyzer.analyze(ctx)
            analysis.project_id = self.project_id
            await self._save_analysis(analysis)
            yield AgentEvent(
                type="analysis_ready",
                message="프리미엄 분석 완료",
                data={"project_id": self.project_id},
            )
        except Exception as e:
            # 분석 실패해도 VOC 수집 완료는 유지
            yield AgentEvent(
                type="analysis_error",
                message=f"프리미엄 분석 실패 (무시됨): {e}",
            )

        ctx.state = AgentState.COMPLETED
        await self._update_project_status("completed")

        yield AgentEvent(
            type="completed",
            message="VOC 수집 완료",
            data=result.get("summary", {}),
        )

    async def _update_project_status(self, status: str):
        db = await get_db()
        try:
            await db.execute(
                "UPDATE projects SET status = ? WHERE id = ?",
                (status, self.project_id),
            )
            await db.commit()
        finally:
            await db.close()

    async def _save_analysis(self, analysis):
        from models.schemas import ReportAnalysis
        db = await get_db()
        try:
            await db.execute(
                """INSERT OR REPLACE INTO report_analysis (project_id, analysis_json)
                   VALUES (?, ?)""",
                (analysis.project_id, analysis.model_dump_json()),
            )
            await db.commit()
        finally:
            await db.close()

    async def _log_agent_run(self, ctx: AgentContext, eval_result) -> None:
        """각 이터레이션 평가 결과를 agent_runs 테이블에 기록"""
        import uuid as _uuid
        db = await get_db()
        try:
            plan_json = ctx.plan.model_dump_json() if ctx.plan else "{}"
            gaps_json = json.dumps(eval_result.gaps, ensure_ascii=False)
            await db.execute(
                """INSERT OR IGNORE INTO agent_runs
                   (id, project_id, iteration, state, plan_json, gaps_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    _uuid.uuid4().hex[:16],
                    self.project_id,
                    ctx.iteration,
                    ctx.state.value if hasattr(ctx.state, "value") else str(ctx.state),
                    plan_json,
                    gaps_json,
                ),
            )
            await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("[loop] _log_agent_run failed: %s", e)
        finally:
            await db.close()

    async def _save_items(self, ctx: AgentContext):
        db = await get_db()
        try:
            for item in ctx.collected_items:
                await db.execute(
                    """INSERT OR IGNORE INTO voc_items
                    (id, project_id, platform, sentiment, original_text,
                     translated_text, source_url, author, date, topics_json,
                     content_hash, confidence, confidence_label,
                     collection_method, approved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.id,
                        item.project_id,
                        item.platform,
                        item.sentiment,
                        item.original_text,
                        item.translated_text,
                        item.source_url,
                        item.author,
                        item.date,
                        json.dumps(item.topics, ensure_ascii=False),
                        item.content_hash,
                        item.confidence,
                        item.confidence_label,
                        item.collection_method,
                        int(item.approved),
                    ),
                )
            await db.commit()
        finally:
            await db.close()
