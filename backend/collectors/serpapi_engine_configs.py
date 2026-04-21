"""SerpApi 엔진별 파라미터 빌더 + 응답 URL 추출기.

지원 엔진:
  검색 엔진: google, naver, yahoo_jp, yandex, baidu
  리뷰/쇼핑: ebay, walmart, home_depot, google_shopping, amazon
"""
from __future__ import annotations

from typing import Optional

# VOC 수집에 사용할 수 있는 SerpApi 엔진 집합
SERPAPI_ENGINES: set[str] = {
    "google",
    "naver",
    "yahoo_jp",
    "yandex",
    "baidu",
    "ebay",
    "walmart",
    "home_depot",
    "google_shopping",
    "amazon",
}

# geo params(gl/lr/hl)가 필요 없는 엔진
# — 지역 특화 엔진이거나 자체 도메인 파라미터로 지역을 처리함
ENGINES_NO_GEO: set[str] = {
    "naver",
    "yahoo_jp",
    "yandex",
    "baidu",
    "walmart",
    "home_depot",
}

# eBay 시장별 도메인
EBAY_DOMAINS: dict[str, str] = {
    "us": "ebay.com",
    "gb": "ebay.co.uk",
    "de": "ebay.de",
    "it": "ebay.it",
    "fr": "ebay.fr",
    "es": "ebay.es",
    "au": "ebay.com.au",
    "ca": "ebay.ca",
    "nl": "ebay.nl",
}

# Amazon 시장별 도메인
AMAZON_DOMAINS: dict[str, str] = {
    "us": "amazon.com",
    "jp": "amazon.co.jp",
    "de": "amazon.de",
    "gb": "amazon.co.uk",
    "fr": "amazon.fr",
    "it": "amazon.it",
    "es": "amazon.es",
    "ca": "amazon.ca",
    "br": "amazon.com.br",
    "in": "amazon.in",
    "mx": "amazon.com.mx",
    "au": "amazon.com.au",
    "ae": "amazon.ae",
    "sg": "amazon.sg",
    "kr": "amazon.co.kr",
    "cn": "amazon.cn",
}


def build_engine_params(
    engine: str,
    query: str,
    max_results: int,
    api_key: str,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    lr: Optional[str] = None,
) -> dict:
    """엔진별 SerpApi 파라미터 딕셔너리 생성.

    각 엔진은 검색어 키(q / query / p / text / _nkw / k)가 다름에 주의.
    """
    base: dict = {"api_key": api_key, "engine": engine, "no_cache": "false"}

    if engine == "google":
        p = {
            **base,
            "q": query,
            "num": min(max(max_results, 1), 20),
            "device": "desktop",
        }
        if gl:
            p["gl"] = gl
        if hl:
            p["hl"] = hl
        if lr:
            p["lr"] = lr

    elif engine == "naver":
        # Naver: 쿼리 키 = "query" (not "q")
        p = {**base, "query": query}

    elif engine == "yahoo_jp":
        # Yahoo Japan: 쿼리 키 = "p" (Yahoo 전통 파라미터)
        p = {**base, "p": query}

    elif engine == "yandex":
        # Yandex: 쿼리 키 = "text"
        p = {**base, "text": query}

    elif engine == "baidu":
        # Baidu: 쿼리 키 = "q"
        p = {**base, "q": query}

    elif engine == "ebay":
        # eBay: 키워드 파라미터 = "_nkw", 시장별 도메인
        p = {**base, "_nkw": query, "LH_BIN": "1"}
        p["ebay_domain"] = EBAY_DOMAINS.get((gl or "us").lower(), "ebay.com")

    elif engine == "walmart":
        # Walmart: 쿼리 키 = "query" (Naver와 동일하지만 다른 엔진)
        p = {**base, "query": query}

    elif engine == "home_depot":
        # Home Depot: 쿼리 키 = "q"
        p = {**base, "q": query}

    elif engine == "google_shopping":
        # Google Shopping: 쿼리 키 = "q", geo params 지원
        p = {**base, "q": query}
        if gl:
            p["gl"] = gl
        if hl:
            p["hl"] = hl

    elif engine == "amazon":
        # Amazon: 키워드 파라미터 = "k", 시장별 도메인
        p = {**base, "k": query}
        p["amazon_domain"] = AMAZON_DOMAINS.get((gl or "us").lower(), "amazon.com")

    else:
        # 미지원 엔진: Google 기본 파라미터로 폴백
        p = {**base, "q": query}

    return p


def extract_url_tuples(
    engine: str, raw: dict
) -> list[tuple[str, str, str]]:
    """엔진별 SerpApi 응답 → (url, title, snippet) 리스트로 정규화.

    모든 엔진의 결과를 동일한 3-tuple 형태로 반환하여
    web_reader.extract_from_url_with_session()에 넘길 수 있도록 함.
    """
    results: list[tuple[str, str, str]] = []

    if engine == "google":
        # 기존 serpapi_models.py 파서 위임 (가장 안정적)
        from collectors.serpapi_models import parse_serpapi_response
        return parse_serpapi_response(raw).to_url_tuples()

    elif engine == "naver":
        # blog_results(블로그) + cafe_results(카페) = 고품질 한국어 VOC
        # organic_results는 보조로 추가
        for section in ("blog_results", "cafe_results", "organic_results"):
            for r in raw.get(section, []):
                url = r.get("link", "")
                title = r.get("title", "")
                # 네이버 블로그/카페는 "description" 필드 사용
                snippet = r.get("description") or r.get("snippet", "")
                if url:
                    results.append((url, title, snippet))

    elif engine in ("yahoo_jp", "yandex", "baidu"):
        # 세 엔진 모두 표준 organic_results 구조
        for r in raw.get("organic_results", []):
            url = r.get("link", "")
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            if url:
                results.append((url, title, snippet))

    elif engine == "ebay":
        for r in raw.get("organic_results", []):
            url = r.get("link", "")
            title = r.get("title", "")
            reviews = r.get("reviews", {}) or {}
            rating = reviews.get("rating", "")
            count = reviews.get("count", "")
            snippet = f"Rating: {rating}/5 ({count} reviews)" if rating else ""
            if url:
                results.append((url, title, snippet))

    elif engine == "walmart":
        for r in raw.get("organic_results", []):
            # Walmart 전용 필드명: product_page_url
            url = r.get("product_page_url", "") or r.get("link", "")
            title = r.get("title", "")
            snippet = (r.get("description") or "")[:200]
            if url:
                results.append((url, title, snippet))

    elif engine == "home_depot":
        # Home Depot은 "products" 키를 사용
        for r in raw.get("products", []):
            url = r.get("link", "")
            title = r.get("title", "")
            reviews = r.get("reviews", {}) or {}
            rating = reviews.get("rating", "")
            snippet = f"Rating: {rating}/5" if rating else ""
            if url:
                results.append((url, title, snippet))

    elif engine == "google_shopping":
        # Google Shopping은 "shopping_results" 키를 사용
        for r in raw.get("shopping_results", []):
            url = r.get("link", "")
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            if url:
                results.append((url, title, snippet))

    elif engine == "amazon":
        for r in raw.get("organic_results", []):
            url = r.get("link", "")
            title = r.get("title", "")
            rating = r.get("rating", "")
            reviews = r.get("reviews", "")
            snippet = f"Rating: {rating}/5 ({reviews} reviews)" if rating else ""
            if url:
                results.append((url, title, snippet))

    return results
