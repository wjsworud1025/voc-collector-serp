"""Stage 3 — SerpApi Pydantic 모델 단위 테스트 (0 credits, fixture 사용)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.serpapi_models import (
    SerpApiOrganicResult,
    SerpApiResponse,
    SerpApiRichSnippet,
    parse_serpapi_response,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "serpapi"


# ── Fixture 로딩 헬퍼 ────────────────────────────────────────────────────────

def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_us_ice_maker_parses():
    raw = load_fixture("us_ice_maker_organic.json")
    resp = parse_serpapi_response(raw)
    assert resp.is_success(), f"Expected success, got error={resp.error}"
    assert len(resp.organic_results) >= 5, f"Expected >=5, got {len(resp.organic_results)}"
    tuples = resp.to_url_tuples()
    assert all(url.startswith("http") for url, _, _ in tuples), "All URLs must start with http"


def test_de_eismaschine_parses():
    raw = load_fixture("de_eismaschine_organic.json")
    resp = parse_serpapi_response(raw)
    assert resp.is_success(), f"Expected success, got error={resp.error}"
    # 독일어 결과: .de 도메인 또는 독일어 사이트
    tuples = resp.to_url_tuples()
    assert len(tuples) >= 5, f"Expected >=5 urls, got {len(tuples)}"


def test_it_macchina_ghiaccio_parses():
    raw = load_fixture("it_macchina_ghiaccio_organic.json")
    resp = parse_serpapi_response(raw)
    assert resp.is_success(), f"Expected success, got error={resp.error}"
    assert len(resp.organic_results) >= 5


def test_empty_results_handled():
    raw = load_fixture("empty_organic_results.json")
    resp = parse_serpapi_response(raw)
    assert not resp.is_success()
    assert resp.organic_results == []
    # to_url_tuples should be empty, not raise
    assert resp.to_url_tuples() == []


def test_error_quota_exhausted():
    raw = load_fixture("error_quota_exhausted.json")
    resp = parse_serpapi_response(raw)
    assert resp.error is not None
    assert "run out" in resp.error.lower() or "searches" in resp.error.lower()
    assert not resp.is_success()


def test_error_invalid_key():
    raw = load_fixture("error_invalid_key.json")
    resp = parse_serpapi_response(raw)
    assert resp.error is not None
    assert not resp.is_success()


def test_best_link_fallback():
    """link가 없을 때 redirect_link로 폴백"""
    r = SerpApiOrganicResult(redirect_link="https://example.com/page")
    assert r.best_link == "https://example.com/page"


def test_best_link_prefers_direct():
    """link가 있으면 redirect_link보다 우선"""
    r = SerpApiOrganicResult(
        link="https://direct.example.com",
        redirect_link="https://google.com/url?q=https://direct.example.com",
    )
    assert r.best_link == "https://direct.example.com"


def test_best_snippet_with_rich_snippet():
    """rich_snippet.top.extensions가 best_snippet에 포함"""
    r = SerpApiOrganicResult(
        snippet="Great portable ice maker",
        rich_snippet=SerpApiRichSnippet(top={"extensions": ["Rating: 4.5/5", "$89"]}),
    )
    assert "Great portable ice maker" in r.best_snippet
    assert "Rating: 4.5/5" in r.best_snippet
    assert "$89" in r.best_snippet


def test_parse_ignores_extra_fields():
    """SerpApi 신규 필드 추가 시 extra=allow로 파싱 성공"""
    raw = {
        "organic_results": [
            {
                "position": 1,
                "title": "Test",
                "link": "https://example.com",
                "future_field_xyz": "some_value",   # 모르는 필드
                "nested_unknown": {"a": 1},
            }
        ],
        "search_metadata": {"id": "test", "status": "Success"},
    }
    resp = parse_serpapi_response(raw)
    assert len(resp.organic_results) == 1
    assert resp.organic_results[0].title == "Test"


def test_to_url_tuples_filters_empty_urls():
    """best_link가 빈 경우 to_url_tuples에서 제외"""
    raw = {
        "organic_results": [
            {"position": 1, "title": "No link result"},   # link=None, redirect_link=None
            {"position": 2, "title": "Has link", "link": "https://example.com"},
        ]
    }
    resp = parse_serpapi_response(raw)
    tuples = resp.to_url_tuples()
    assert len(tuples) == 1
    assert tuples[0][0] == "https://example.com"
