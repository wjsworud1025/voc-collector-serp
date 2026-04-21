"""VOC Collector — FastAPI 메인 서버"""

from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from routers import projects, agent, reports

load_dotenv()


async def _load_settings_to_env():
    """DB에 저장된 API 키를 프로세스 환경변수로 반영"""
    import os
    from models.database import get_db
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT key, value FROM settings")
        for row in rows:
            if row["value"]:
                os.environ[row["key"]] = row["value"]
    finally:
        await db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 DB 초기화 + 저장된 API 키 환경변수 반영"""
    await init_db()
    await _load_settings_to_env()
    yield


app = FastAPI(
    title="VOC Collector",
    description="글로벌 VOC 수집 및 리포팅 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["프로젝트"])
app.include_router(agent.router, prefix="/api/agent", tags=["에이전트"])
app.include_router(reports.router, prefix="/api/reports", tags=["보고서"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/settings")
async def get_settings():
    from models.database import get_db
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}
    finally:
        await db.close()


@app.put("/api/settings")
async def update_setting(data: dict):
    import os
    from models.database import get_db
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (data["key"], data["value"]),
        )
        await db.commit()
        # 실행 중인 프로세스의 환경변수도 즉시 갱신
        if data.get("value"):
            os.environ[data["key"]] = data["value"]
        return {"ok": True}
    finally:
        await db.close()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
