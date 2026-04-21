"""SQLite 데이터베이스 — 스키마 및 연결 관리"""

import aiosqlite
import os

from paths import get_db_path

DB_PATH = get_db_path()


async def get_db() -> aiosqlite.Connection:
    """DB 연결 반환 (FastAPI Depends용)"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """테이블 생성 (앱 시작 시 1회)"""
    db = await get_db()
    try:
        # ── 기존 테이블 (executescript 일괄 생성) ──
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                user_request TEXT NOT NULL,
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                project_id TEXT REFERENCES projects(id),
                iteration INTEGER,
                state TEXT,
                plan_json TEXT,
                gaps_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS voc_items (
                id TEXT PRIMARY KEY,
                project_id TEXT REFERENCES projects(id),
                platform TEXT,
                sentiment TEXT,
                original_text TEXT,
                translated_text TEXT,
                source_url TEXT NOT NULL,
                author TEXT,
                date TEXT,
                topics_json TEXT,
                content_hash TEXT,
                confidence REAL,
                confidence_label TEXT,
                collection_method TEXT,
                approved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_voc_dedup
                ON voc_items(project_id, content_hash);

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES ('GEMINI_API_KEY', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('GOOGLE_CSE_API_KEY', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('GOOGLE_CSE_CX', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('YOUTUBE_API_KEY', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('SERPAPI_KEY', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('GEMINI_MODEL', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('GEMINI_ANALYSIS_MODEL', '');
        """)

        # ── 프리미엄 분석 테이블 (별도 execute — 기존 DB 마이그레이션 보장) ──
        await db.execute("""
            CREATE TABLE IF NOT EXISTS report_analysis (
                project_id TEXT PRIMARY KEY,
                analysis_json TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    finally:
        await db.close()
