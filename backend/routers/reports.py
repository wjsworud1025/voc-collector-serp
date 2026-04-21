"""보고서 생성 라우터"""

import json
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.database import get_db
from models.schemas import ReportAnalysis, VocItem
from reporter import generate_pdf
from paths import get_reports_dir

router = APIRouter()


class ReportRequest(BaseModel):
    report_type: str = "standard"  # "standard" | "executive" | "detailed" | "premium"


@router.post("/{project_id}/generate")
async def generate_report(project_id: str, req: Optional[ReportRequest] = None):
    """승인된 VOC → PDF 보고서 생성"""
    report_type = (req.report_type if req else None) or "standard"

    db = await get_db()
    try:
        # 프로젝트 조회
        rows = await db.execute_fetchall(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")
        project = rows[0]

        # 승인된 VOC 조회
        voc_rows = await db.execute_fetchall(
            "SELECT * FROM voc_items WHERE project_id = ? AND approved = 1 ORDER BY sentiment, confidence DESC",
            (project_id,),
        )
    finally:
        await db.close()

    if not voc_rows:
        raise HTTPException(status_code=400, detail="승인된 VOC가 없습니다. 먼저 검토 화면에서 항목을 승인해 주세요.")

    # Row → VocItem
    voc_items = [
        VocItem(
            id=r["id"],
            project_id=r["project_id"],
            platform=r["platform"] or "web",
            sentiment=r["sentiment"] or "neutral",
            original_text=r["original_text"] or "",
            translated_text=r["translated_text"] or "",
            source_url=r["source_url"],
            author=r["author"],
            date=r["date"],
            topics=json.loads(r["topics_json"] or "[]"),
            content_hash=r["content_hash"] or "",
            confidence=r["confidence"] or 0.0,
            confidence_label=r["confidence_label"] or "추정",
            collection_method=r["collection_method"] or "tier2_static",
            approved=bool(r["approved"]),
        )
        for r in voc_rows
    ]

    # 프리미엄 보고서: DB에서 분석 데이터 로드
    analysis = None
    if report_type == "premium":
        try:
            analysis = await _load_analysis(project_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"분석 데이터 로드 오류: {e}")
        if analysis is None:
            raise HTTPException(
                status_code=400,
                detail="프리미엄 분석 데이터가 없습니다. '분석 생성' 버튼을 눌러 먼저 생성해 주세요."
            )

    try:
        pdf_path = generate_pdf(
            project_id=project_id,
            project_name=project["name"],
            user_request=project["user_request"],
            voc_items=voc_items,
            report_type=report_type,
            analysis=analysis,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 중 오류: {e}")

    return {
        "ok": True,
        "project_id": project_id,
        "report_type": report_type,
        "voc_count": len(voc_items),
        "download_url": f"/api/reports/{project_id}/download?report_type={report_type}",
    }


@router.get("/{project_id}/download")
async def download_report(
    project_id: str,
    report_type: str = Query(default="standard"),
):
    """PDF 보고서 다운로드"""
    pdf_path = os.path.join(get_reports_dir(), f"{project_id}_{report_type}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=404,
            detail="보고서 파일이 없습니다. 먼저 생성 버튼을 눌러 주세요.",
        )
    type_label = {"standard": "표준", "executive": "경영진요약", "detailed": "상세"}.get(report_type, report_type)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"voc_report_{project_id}_{type_label}.pdf",
    )


@router.get("/{project_id}/status")
async def report_status(
    project_id: str,
    report_type: str = Query(default="standard"),
):
    """보고서 파일 존재 여부 확인"""
    pdf_path = os.path.join(get_reports_dir(), f"{project_id}_{report_type}.pdf")
    exists = os.path.exists(pdf_path)
    size = os.path.getsize(pdf_path) if exists else 0
    return {"exists": exists, "size": size, "report_type": report_type}


@router.get("/{project_id}/analysis/status")
async def analysis_status(project_id: str):
    """프리미엄 분석 데이터 존재 여부 확인"""
    try:
        analysis = await _load_analysis(project_id)
        return {
            "exists": analysis is not None,
            "generated_at": analysis.generated_at.isoformat() if analysis else None,
        }
    except Exception:
        return {"exists": False, "generated_at": None}


@router.post("/{project_id}/analysis/regenerate")
async def regenerate_analysis(project_id: str, background_tasks: BackgroundTasks):
    """프리미엄 분석 재생성 (승인된 VOC 기반)"""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

        voc_rows = await db.execute_fetchall(
            "SELECT * FROM voc_items WHERE project_id = ? AND approved = 1",
            (project_id,),
        )
    finally:
        await db.close()

    if not voc_rows:
        raise HTTPException(status_code=400, detail="승인된 VOC가 없습니다")

    voc_items = [
        VocItem(
            id=r["id"],
            project_id=r["project_id"],
            platform=r["platform"] or "web",
            sentiment=r["sentiment"] or "neutral",
            original_text=r["original_text"] or "",
            translated_text=r["translated_text"] or "",
            source_url=r["source_url"],
            author=r["author"],
            date=r["date"],
            topics=json.loads(r["topics_json"] or "[]"),
            content_hash=r["content_hash"] or "",
            confidence=r["confidence"] or 0.0,
            confidence_label=r["confidence_label"] or "추정",
            collection_method=r["collection_method"] or "tier2_static",
            approved=bool(r["approved"]),
        )
        for r in voc_rows
    ]

    background_tasks.add_task(_run_analysis, project_id, rows[0], voc_items)
    return {"ok": True, "message": "프리미엄 분석을 백그라운드에서 생성 중입니다"}


async def _run_analysis(project_id: str, project_row, voc_items: list[VocItem]):
    """백그라운드 분석 실행"""
    from agent.analyzer import Analyzer
    from agent.state import AgentContext
    from models.schemas import ResearchPlan, SearchTask

    try:
        analyzer = Analyzer()
        # 가상 컨텍스트 구성
        ctx = AgentContext()
        ctx.collected_items = voc_items
        ctx.plan = ResearchPlan(
            market=project_row["name"].split(" ")[0] if project_row["name"] else "글로벌",
            product_category=project_row["name"],
            target_demographic="소비자",
            keywords=[],
            languages=["ko"],
            platforms=["google"],
            tasks=[],
        )
        analysis = await analyzer.analyze(ctx)
        analysis.project_id = project_id

        db = await get_db()
        try:
            await _ensure_analysis_table(db)
            await db.execute(
                "INSERT OR REPLACE INTO report_analysis (project_id, analysis_json) VALUES (?, ?)",
                (project_id, analysis.model_dump_json()),
            )
            await db.commit()
        finally:
            await db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("분석 백그라운드 실패: %s", e)


async def _ensure_analysis_table(db) -> None:
    """report_analysis 테이블이 없으면 생성 (마이그레이션 안전장치)"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS report_analysis (
            project_id TEXT PRIMARY KEY,
            analysis_json TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()


async def _load_analysis(project_id: str) -> "ReportAnalysis | None":
    """DB에서 ReportAnalysis 로드"""
    db = await get_db()
    try:
        await _ensure_analysis_table(db)
        rows = await db.execute_fetchall(
            "SELECT analysis_json FROM report_analysis WHERE project_id = ?",
            (project_id,),
        )
        if not rows:
            return None
        return ReportAnalysis.model_validate_json(rows[0]["analysis_json"])
    finally:
        await db.close()
