"""에이전트 실행 + SSE 스트림 라우터"""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.schemas import AgentEvent

router = APIRouter()

# 프로젝트별 에이전트 실행 상태 (메모리)
_running_agents: dict[str, bool] = {}


@router.post("/{project_id}/start")
async def start_agent(project_id: str):
    """에이전트 수집 시작 → SSE 스트림 반환"""

    if _running_agents.get(project_id):
        return {"error": "이미 실행 중입니다"}

    async def event_stream():
        _running_agents[project_id] = True
        try:
            import os
            from agent.loop import ResearchAgent
            from models.database import get_db

            # 에이전트 시작 전 DB의 API 키를 env에 반영 (UI 저장 키 즉시 적용)
            _db = await get_db()
            try:
                _rows = await _db.execute_fetchall("SELECT key, value FROM settings")
                for _r in _rows:
                    if _r["value"]:
                        os.environ[_r["key"]] = _r["value"]
            finally:
                await _db.close()

            db = await get_db()
            try:
                rows = await db.execute_fetchall(
                    "SELECT user_request FROM projects WHERE id = ?",
                    (project_id,),
                )
                if not rows:
                    yield AgentEvent(
                        type="error", message="프로젝트를 찾을 수 없습니다"
                    ).to_sse()
                    return

                user_request = rows[0]["user_request"]
            finally:
                await db.close()

            agent = ResearchAgent(project_id=project_id)
            async for event in agent.run(user_request):
                if not _running_agents.get(project_id):
                    yield AgentEvent(
                        type="stopped", message="사용자가 중단했습니다"
                    ).to_sse()
                    return
                yield event.to_sse()

        except Exception as e:
            yield AgentEvent(
                type="error", message=f"에이전트 오류: {str(e)}"
            ).to_sse()
        finally:
            _running_agents.pop(project_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{project_id}/stop")
async def stop_agent(project_id: str):
    """에이전트 중단"""
    _running_agents[project_id] = False
    return {"ok": True, "message": "중단 요청됨"}
