"""소스 분류 — 규칙 기반 (LLM 불필요)"""

from urllib.parse import urlparse

SOURCE_REGISTRY: dict[str, dict] = {
    "reddit.com": {"collector": "reddit", "tier": 1},
    "youtube.com": {"collector": "youtube", "tier": 1},
    "youtu.be": {"collector": "youtube", "tier": 1},
}

DEFAULT_CONFIG = {"collector": "web_reader", "tier": 2}


def classify_source(url: str) -> dict:
    """도메인 매칭으로 수집 방식 결정. LLM 호출 없음."""
    try:
        domain = urlparse(url).netloc.lower()
        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]

        for pattern, config in SOURCE_REGISTRY.items():
            if domain.endswith(pattern):
                return config
    except Exception:
        pass

    return DEFAULT_CONFIG
