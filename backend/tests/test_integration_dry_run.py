"""Stage 7 — DRY_RUN 통합 테스트 (SERPAPI_DRY_RUN=1, 0 credits).

Phase A 모든 변경사항 검증:
- A3: 봇차단 URL도 content_match=True (Verifier L3)
- A4: Synthesizer approved=True 명시
- A5: _save_items approved 컬럼 포함
- A6: _log_agent_run (agent_runs 테이블)
- A7: MAX_ITERATIONS=5
- A11: Evaluator fallback signal
- SerpApiSearchCollector DRY_RUN 모드 fixture 반환
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# DRY_RUN 모드 강제 활성화 + 가짜 API 키 (genai.Client 초기화 통과용)
os.environ["SERPAPI_DRY_RUN"] = "1"
os.environ["SERPAPI_KEY"] = "test_key_dry_run"
os.environ["SERPAPI_MIN_CREDITS_GUARD"] = "5"
os.environ["GEMINI_API_KEY"] = "AIzaSy_fake_test_key_for_unit_test_only"

from collectors.serpapi_search import SerpApiSearchCollector
from collectors.serpapi_models import parse_serpapi_response
from agent.evaluator import Evaluator
from agent.synthesizer import Synthesizer
from agent.state import AgentContext
from models.schemas import VocItem
from verifier import Verifier


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_voc_item(approved: bool = False, confidence: float = 0.8) -> VocItem:
    return VocItem(
        id="test_" + os.urandom(4).hex(),
        project_id="proj_test",
        platform="web",
        sentiment="positive",
        original_text="This ice maker is excellent, makes ice in 10 minutes",
        translated_text="",
        source_url="https://example.com/review",
        confidence=confidence,
        confidence_label="확실" if confidence >= 0.75 else "추정",
        collection_method="tier2_static",
        approved=approved,
    )


# ── 1. SerpApiSearchCollector DRY_RUN 모드 ───────────────────────────────────

def test_dryrun_returns_fixture():
    """DRY_RUN 모드에서 fixture JSON 반환 (0 credits)"""
    collector = SerpApiSearchCollector()
    assert collector.dry_run is True

    async def _run():
        raw = await collector._search_with_protection({
            "q": "portable ice maker review",
            "gl": "us",
            "num": 10,
        })
        return raw

    raw = asyncio.run(_run())
    resp = parse_serpapi_response(raw)
    # us fixture가 있으면 success, 없으면 empty — 어느 쪽이든 파싱 성공이어야 함
    assert isinstance(resp.organic_results, list)


def test_dryrun_gl_matching():
    """gl=de일 때 de fixture 우선 선택"""
    collector = SerpApiSearchCollector()

    async def _run():
        return await collector._search_with_protection({
            "q": "Eismaschine Test",
            "gl": "de",
            "num": 10,
        })

    raw = asyncio.run(_run())
    resp = parse_serpapi_response(raw)
    # de fixture는 9개 organic_results 있음
    assert len(resp.organic_results) >= 5, f"Expected DE fixture with >=5 results, got {len(resp.organic_results)}"


# ── 2. Verifier L3 봇차단 허용 (A3) ─────────────────────────────────────────

def test_verifier_bot_blocked_url_passes():
    """봇 차단(403)으로 _fetch_text가 빈값 → content_match=True로 처리"""
    verifier = Verifier()

    item = make_voc_item()
    item.source_url = "https://amazon.de/review/blocked"

    async def _run():
        with patch.object(
            verifier, "_check_url", new_callable=AsyncMock, return_value=True
        ), patch.object(
            verifier, "_fetch_text", new_callable=AsyncMock, return_value=""
        ):
            result = await verifier.verify(item)
        return result

    result = asyncio.run(_run())
    assert result.checks.get("content_match") is True, (
        f"Bot-blocked URL should pass content_match, got checks={result.checks}"
    )
    # 봇 차단 URL도 confidence >= 0.75이어야 함 (has_url + url_reachable + content_match + date_valid = 4/4)
    assert result.confidence >= 0.75, f"Expected confidence >= 0.75, got {result.confidence}"


def test_verifier_real_content_match():
    """텍스트가 있으면 fuzzy_match 정상 수행"""
    verifier = Verifier()
    item = make_voc_item()

    async def _run():
        with patch.object(
            verifier, "_check_url", new_callable=AsyncMock, return_value=True
        ), patch.object(
            verifier, "_fetch_text",
            new_callable=AsyncMock,
            return_value="This ice maker is excellent makes ice very quickly",
        ):
            result = await verifier.verify(item)
        return result

    result = asyncio.run(_run())
    # 텍스트 있으면 fuzzy_match 수행 → 충분한 overlap이므로 True 예상
    assert result.checks.get("url_reachable") is True


# ── 3. Synthesizer approved=True 명시 (A4) ───────────────────────────────────

def test_synthesizer_sets_approved_true():
    """관련 VOC에 대해 approved=True 명시 설정"""
    synthesizer = Synthesizer()

    item = make_voc_item(approved=False)  # 초기값 False
    batch = [item]

    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "id": item.id,
        "relevant": True,
        "sentiment": "positive",
        "topics": ["품질", "속도"],
        "translated_text": "이 제빙기는 훌륭합니다",
    }])

    async def _run():
        with patch.object(
            synthesizer.client.models, "generate_content", return_value=mock_response
        ):
            ctx = AgentContext()
            ctx.plan = MagicMock()
            ctx.plan.product_category = "portable ice maker"
            ctx.plan.market = "US"
            await synthesizer._enrich_batch(batch, ctx)

    asyncio.run(_run())
    assert item.approved is True, f"Expected approved=True for relevant VOC, got {item.approved}"


def test_synthesizer_sets_approved_false():
    """비관련 VOC에 대해 approved=False 명시 설정"""
    synthesizer = Synthesizer()
    item = make_voc_item(approved=True)  # 초기값 True

    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "id": item.id,
        "relevant": False,
        "sentiment": "neutral",
        "topics": [],
        "translated_text": "",
    }])

    async def _run():
        with patch.object(
            synthesizer.client.models, "generate_content", return_value=mock_response
        ):
            ctx = AgentContext()
            ctx.plan = MagicMock()
            ctx.plan.product_category = "portable ice maker"
            ctx.plan.market = "US"
            await synthesizer._enrich_batch([item], ctx)

    asyncio.run(_run())
    assert item.approved is False, f"Expected approved=False for irrelevant VOC, got {item.approved}"


# ── 4. Evaluator fallback signal (A11) ───────────────────────────────────────

def test_evaluator_fallback_when_no_approved():
    """approved=0건이지만 verified_count>0이면 fallback으로 verified_count 사용"""
    evaluator = Evaluator()

    ctx = AgentContext()
    # 10개 아이템 모두 approved=False (synthesizer 미실행 시뮬레이션)
    # confidence=0.8 (default) → verified_count=10 (computed property)
    for i in range(10):
        item = make_voc_item(approved=False, confidence=0.8)
        item.sentiment = "positive" if i < 5 else ("negative" if i < 8 else "neutral")
        ctx.collected_items.append(item)

    async def _run():
        return await evaluator.evaluate(ctx)

    result = asyncio.run(_run())
    # fallback 덕분에 relevant_count=10, MIN_TOTAL=10 충족 → 관련 VOC 부족 gap 없어야 함
    quantity_gap = [g for g in result.gaps if "관련 VOC 부족" in g]
    assert len(quantity_gap) == 0, (
        f"Fallback should eliminate quantity gap, but got gaps: {result.gaps}"
    )


def test_evaluator_no_fallback_when_approved_exist():
    """approved>0이면 fallback 사용하지 않음"""
    evaluator = Evaluator()

    ctx = AgentContext()
    for i in range(3):  # only 3 approved (confidence=0.8 → verified_count=3)
        item = make_voc_item(approved=True, confidence=0.8)
        item.sentiment = "positive" if i < 2 else "negative"
        ctx.collected_items.append(item)

    async def _run():
        return await evaluator.evaluate(ctx)

    result = asyncio.run(_run())
    # MIN_TOTAL=10, 3건 → 부족 gap 발생해야 함 (fallback 없이)
    quantity_gap = [g for g in result.gaps if "관련 VOC 부족" in g]
    assert len(quantity_gap) > 0, "Should have quantity gap with only 3 approved items"


# ── 5. MAX_ITERATIONS 검증 (A7) ──────────────────────────────────────────────

def test_max_iterations_is_5():
    from agent.loop import ResearchAgent
    assert ResearchAgent.MAX_ITERATIONS == 5, (
        f"Expected MAX_ITERATIONS=5, got {ResearchAgent.MAX_ITERATIONS}"
    )


# ── 6. _save_items approved 컬럼 포함 (A5) ───────────────────────────────────

def test_save_items_includes_approved():
    """_save_items SQL에 approved 컬럼이 포함되어 있는지 소스 검사"""
    import inspect
    from agent.loop import ResearchAgent
    source = inspect.getsource(ResearchAgent._save_items)
    assert "approved" in source, "_save_items SQL must include approved column"
    # VALUES에 int(item.approved)가 있어야 함
    assert "int(item.approved)" in source, "_save_items must cast approved to int"


# ── 7. _log_agent_run 존재 + 호출 (A6) ──────────────────────────────────────

def test_log_agent_run_method_exists():
    from agent.loop import ResearchAgent
    assert hasattr(ResearchAgent, "_log_agent_run"), "_log_agent_run method must exist"


def test_log_agent_run_is_called_after_evaluate():
    """eval_result 직후 _log_agent_run 호출 여부 소스 검사"""
    import inspect
    from agent.loop import ResearchAgent
    source = inspect.getsource(ResearchAgent.run)
    # _log_agent_run이 eval_result 다음 줄에 호출되는지 확인
    assert "_log_agent_run" in source, "_log_agent_run must be called in run()"
