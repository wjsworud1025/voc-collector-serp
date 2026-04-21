"""프로젝트 CRUD 라우터"""

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.database import get_db
from models.schemas import CreateProjectRequest, ProjectResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse)
async def create_project(req: CreateProjectRequest):
    """새 프로젝트 생성"""
    project_id = uuid.uuid4().hex[:12]
    # LLM이 나중에 이름을 지어주지만, 우선 요청문 앞 20자를 이름으로
    name = req.user_request[:20].strip()

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO projects (id, name, user_request) VALUES (?, ?, ?)",
            (project_id, name, req.user_request),
        )
        await db.commit()
        return ProjectResponse(
            id=project_id,
            name=name,
            user_request=req.user_request,
            status="created",
            created_at="",
            voc_count=0,
        )
    finally:
        await db.close()


@router.get("")
async def list_projects():
    """프로젝트 목록"""
    db = await get_db()
    try:
        rows = await db.execute_fetchall("""
            SELECT p.*, COUNT(v.id) as voc_count
            FROM projects p
            LEFT JOIN voc_items v ON v.project_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """)
        return [
            ProjectResponse(
                id=r["id"],
                name=r["name"],
                user_request=r["user_request"],
                status=r["status"],
                created_at=str(r["created_at"] or ""),
                voc_count=r["voc_count"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.get("/{project_id}")
async def get_project(project_id: str):
    """프로젝트 상세"""
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if not row:
            return {"error": "프로젝트를 찾을 수 없습니다"}
        r = row[0]

        # VOC 목록
        vocs = await db.execute_fetchall(
            "SELECT * FROM voc_items WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        return {
            "project": dict(r),
            "voc_items": [dict(v) for v in vocs],
        }
    finally:
        await db.close()


class VocApprovalRequest(BaseModel):
    approved: int  # 1=승인, -1=제외, 0=미결정


@router.patch("/{project_id}/voc/{voc_id}")
async def update_voc_approval(project_id: str, voc_id: str, req: VocApprovalRequest):
    """VOC 승인/제외 상태 저장"""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE voc_items SET approved = ? WHERE id = ? AND project_id = ?",
            (req.approved, voc_id, project_id),
        )
        await db.commit()
        return {"ok": True, "voc_id": voc_id, "approved": req.approved}
    finally:
        await db.close()
