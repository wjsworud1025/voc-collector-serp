"""조사계획 수립 — 하네스 엔지니어링 v2

적용된 기법:
  - Chain-of-Thought 단계별 추론 구조 (CoT)
  - Few-Shot 예시 (미국 전자제품 · 독일 전자제품)
  - 시장별 Reddit 선택적 허용 (비영어권 활성 커뮤니티 포함)
  - 출력 전 규칙 체크리스트 (constraint enumeration)
  - 태스크 수 고정 (8개) + 감성 분배 명세
  - 후처리 검증 (_validate_and_fix_plan)
  - asyncio.to_thread()로 블로킹 LLM 호출 비동기 처리
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid

from google import genai

logger = logging.getLogger(__name__)

# 503/500 재시도 설정
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0   # 첫 재시도 대기(초), 이후 지수 증가

from agent.state import AgentContext
from market_config import (
    MARKET_CONFIG,
    detect_product_type,
    get_market_context,
    get_native_keywords,
    resolve_market,
    _PRODUCT_TYPE_LABELS,
)
from models.schemas import PlanRevision, ResearchPlan, SearchTask


# ─── 시장별 Reddit 허용 정책 ─────────────────────────────────────────────────
# 영어권: 전면 허용 (all subreddits)
# 비영어권이지만 활성 모국어 커뮤니티 존재: 선택적 허용 (subreddit 목록 제공)
# 활성 모국어 커뮤니티 없음: 금지 (현지 플랫폼 우선)

_REDDIT_COMMUNITIES: dict[str, dict] = {
    # ── 영어권 — 전면 허용 ──────────────────────────────────────────────────
    "미국":    {"allowed": True,  "mode": "full",
               "note": "모든 관련 subreddit 사용 가능 (r/all)"},
    "영국":    {"allowed": True,  "mode": "full",
               "note": "모든 관련 subreddit 사용 가능 (r/unitedkingdom 등)"},
    "호주":    {"allowed": True,  "mode": "full",
               "note": "모든 관련 subreddit 사용 가능 (r/australia 등)"},
    "인도":    {"allowed": True,  "mode": "full",
               "note": "영어 커뮤니티 활발 (r/india, r/IndianGaming, r/IndianSkincareAddicts)"},
    # ── 비영어권 — 선택적 허용 (모국어 활성 커뮤니티 존재) ─────────────────
    "독일": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/de", "r/DACH", "r/germany", "r/FragReddit", "r/Finanzen"],
        "note": (
            "독일어 subreddit 활발. "
            "source='google', query='site:reddit.com/r/de {제품} Erfahrung' 형태 권장. "
            "또는 source='reddit', query='{제품} Erfahrung empfehlen site:reddit.com/r/de'"
        ),
    },
    "프랑스": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/france", "r/AskFrance"],
        "note": (
            "프랑스어 subreddit 존재. "
            "source='google', query='site:reddit.com/r/france {제품} avis' 형태 권장."
        ),
    },
    "이탈리아": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/italy", "r/ItalyInformatica"],
        "note": (
            "이탈리아어 subreddit 존재. "
            "source='google', query='site:reddit.com/r/italy {제품} recensione' 형태 권장."
        ),
    },
    "스페인": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/es", "r/spain", "r/AskSpain"],
        "note": (
            "스페인어 subreddit 존재. "
            "source='google', query='site:reddit.com/r/es {제품} opiniones' 형태 권장."
        ),
    },
    "포르투갈": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/portugal"],
        "note": (
            "포르투갈어 subreddit 존재. "
            "source='google', query='site:reddit.com/r/portugal {제품} avaliação' 형태 권장."
        ),
    },
    "브라질": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/brasil", "r/brdev", "r/investimentos", "r/conversas"],
        "note": (
            "포르투갈어(BR) subreddit 활발. "
            "source='google', query='site:reddit.com/r/brasil {제품} avaliação' 형태 권장."
        ),
    },
    "아르헨티나": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/argentina"],
        "note": "스페인어 subreddit 존재. source='google', query='site:reddit.com/r/argentina {제품}' 권장.",
    },
    "멕시코": {
        "allowed": True,
        "mode": "selective",
        "subreddits": ["r/mexico"],
        "note": "스페인어 subreddit 존재. source='google', query='site:reddit.com/r/mexico {제품}' 권장.",
    },
    # ── 비영어권 — 금지 (활성 모국어 커뮤니티 없음) ────────────────────────
    "한국":      {"allowed": False, "note": "r/korea는 영어 위주. 한국어 커뮤니티 없음 → 다나와·뽐뿌 등 현지 플랫폼 우선."},
    "일본":      {"allowed": False, "note": "r/japan은 영어 위주. 일본어 활동 없음 → 価格.com·Yahoo知恵袋 우선."},
    "대만":      {"allowed": False, "note": "Reddit 사용 낮음 → PTT·Mobile01 우선."},
    "태국":      {"allowed": False, "note": "Reddit 사용 낮음 → Pantip 우선."},
    "베트남":    {"allowed": False, "note": "Reddit 사용 낮음 → VoZ·Tinhte 우선."},
    "인도네시아":{"allowed": False, "note": "Kaskus·Female Daily 등 현지 플랫폼 우선."},
    "말레이시아":{"allowed": False, "note": "Lowyat Forum 등 현지 플랫폼 우선."},
    "이집트":    {"allowed": False, "note": "Reddit 사용 매우 낮음 → 아랍어 YouTube·Forum 우선."},
    "UAE":       {"allowed": False, "note": "Reddit 사용 낮음 → 아랍어 플랫폼 우선."},
    "이스라엘":  {"allowed": False, "note": "히브리어 커뮤니티 없음 → 현지 플랫폼 우선."},
}


def _get_reddit_guidance(market: str) -> str:
    """시장별 Reddit 사용 지침 문자열 생성 (프롬프트 주입용)."""
    cfg = _REDDIT_COMMUNITIES.get(market)
    if cfg is None:
        return "reddit: 해당 시장 정보 없음 — 사용 금지로 처리."
    if not cfg["allowed"]:
        return f"reddit: ❌ 사용 금지 — {cfg['note']}"
    if cfg.get("mode") == "full":
        return f"reddit: ✅ 전면 허용 — {cfg['note']}"
    subreddits_str = ", ".join(cfg.get("subreddits", []))
    return (
        f"reddit: ⚠️ 선택적 허용 — 허용 subreddit: {subreddits_str}\n"
        f"  방법: {cfg['note']}"
    )


def _build_product_type_block(product_type: str) -> str:
    """제품 유형에 따른 검색 전략 힌트 블록 생성 (프롬프트 주입용)."""
    if product_type == "electronics":
        return """
**[전자/가전제품 VOC 수집 전략 — 반드시 적용]:**
- 이 제품은 **전자/가전제품**입니다.
- 한국 시장이면: tasks에 반드시 site:danawa.com, site:enuri.com, site:ppomppu.co.kr 쿼리 포함
  예시: {"source": "google", "query": "site:danawa.com LG 워시타워 리뷰", "language": "ko"}
- 독일 시장: site:computerbase.de, site:idealo.de, site:test.de 활용
- 프랑스 시장: site:lesnumeriques.com, site:clubic.com, site:fnac.com 활용
- 이탈리아 시장: site:hwupgrade.it, site:trovaprezzi.it 활용
- 스페인 시장: site:xataka.com, site:pccomponentes.com, site:idealo.es 활용
- keywords와 filter_keywords에 반드시 전자/가전 특화 VOC 표현 포함:
  한국어: AS후기, 고장, 불량, 수리비, 소음, 진동, 에너지효율, 전기세, 설치후기
  영어: warranty, repair, noise, energy efficiency, defect, malfunction"""

    elif product_type == "cosmetics":
        return """
**[뷰티/화장품 VOC 수집 전략 — 반드시 적용]:**
- 이 제품은 **뷰티/화장품**입니다.
- 한국 시장이면: tasks에 site:hwahae.co.kr, site:oliveyoung.co.kr 쿼리 포함
- keywords에 피부타입, 성분, 부작용, 발림성, 지속력 등 뷰티 특화 표현 포함"""

    elif product_type == "automotive":
        return """
**[자동차/자동차용품 VOC 수집 전략 — 반드시 적용]:**
- keywords에 연비, 내구성, AS, 안전성 등 자동차 특화 표현 포함
- 한국 시장: 보배드림, 클리앙 자동차 게시판, 네이버 자동차 카페 활용"""

    elif product_type == "food":
        return """
**[식품/음료 VOC 수집 전략 — 반드시 적용]:**
- keywords에 맛, 성분, 칼로리, 가성비, 알레르기 등 식품 특화 표현 포함"""

    else:
        return ""


# ─── 감성/관점 분류용 다국어 키워드 (후처리 검증) ─────────────────────────
# 쿼리 문자열을 lower-case로 검사해 각 버킷에 속하는지 판별.
# 한국어·영어·독일어·프랑스어·이탈리아어·스페인어·포르투갈어·일본어·중국어 커버.

_SENTIMENT_KEYWORDS: dict[str, list[str]] = {
    "negative": [
        # 한국어
        "불만", "단점", "고장", "결함", "클레임", "문제", "부작용", "트러블",
        "as후기", "수리", "불량",
        # 영어
        "complaints", "problems", "issues", "defect", "malfunction", "broken",
        "worst", "negative", "fail",
        # 독일어
        "probleme", "nachteile", "defekt", "kaputt", "fehler", "beschwerden",
        "mangel",
        # 프랑스어
        "problèmes", "problemes", "défauts", "defauts", "inconvénients",
        "inconvenients", "panne",
        # 이탈리아어
        "problemi", "difetti", "guasto", "rotto",
        # 스페인어
        "problemas", "defectos", "averia", "avería", "queja",
        # 포르투갈어
        "problemas", "defeitos", "reclamação", "reclamacao",
        # 일본어
        "不具合", "不満", "欠点", "故障", "問題",
        # 중국어
        "问题", "缺点", "故障",
    ],
    "positive": [
        # 한국어
        "추천", "만족", "후기", "장점", "좋은", "솔직", "내돈내산",
        # 영어
        "review", "recommend", "best", "good", "worth it", "love",
        # 독일어
        "empfehlen", "empfehlung", "gut", "positiv", "erfahrung", "test",
        # 프랑스어
        "avis", "recommande", "test", "bon",
        # 이탈리아어
        "recensione", "consigliato", "buono",
        # 스페인어
        "opiniones", "recomendar", "bueno", "reseña", "resena",
        # 포르투갈어
        "opinião", "opiniao", "avaliação", "avaliacao", "recomendo",
        # 일본어
        "口コミ", "レビュー", "評判", "おすすめ",
        # 중국어
        "推荐", "评价", "好用",
    ],
    "comparison": [
        "vs", "비교", "vergleich", "comparatif", "comparaison", "comparison",
        "comparativa", "confronto", "比較", "对比", "versus",
    ],
    "feature": [
        # 소음/에너지/설치/성능
        "소음", "진동", "에너지", "전기세", "설치", "소비전력", "효율",
        "noise", "energy", "installation", "performance", "battery", "size",
        "lärm", "energie", "installation", "leistung", "verbrauch",
        "bruit", "énergie", "energie", "installation", "performance",
        "rumore", "energia", "installazione", "prestazioni",
        "ruido", "energía", "energia", "instalación", "instalacion", "rendimiento",
        "발림성", "지속력", "성분", "texture", "ingredient",
    ],
}


def _classify_query_sentiment(query: str) -> set[str]:
    """쿼리 문자열에서 감성/관점 버킷(set)을 분류. 다중 소속 가능.

    예: "portable ice maker complaints vs competitors" → {"negative", "comparison"}
    """
    q_lower = query.lower()
    buckets: set[str] = set()
    for bucket, keywords in _SENTIMENT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in q_lower:
                buckets.add(bucket)
                break
    return buckets


# ─── Few-Shot 예시 (고정 문자열, 프롬프트에 삽입) ──────────────────────────

_FEW_SHOT_EXAMPLES = """
## ■ 출력 예시 (참고용 — 형식과 분배 방식을 반드시 따르세요)

### 예시 A: 미국 시장 · portable ice maker (전자제품)
```json
{
  "market": "미국",
  "product_category": "portable ice maker",
  "target_demographic": "가정용 주방가전 구매자, 야외활동 애호가",
  "keywords": ["ice maker", "nugget ice", "countertop ice", "portable ice", "review", "complaints", "problems", "worth it"],
  "filter_keywords": ["ice maker", "nugget ice", "portable ice maker", "countertop ice maker", "complaints", "defects", "malfunction", "noise", "slow production", "warranty", "review", "best", "problems", "worth it"],
  "languages": ["en"],
  "platforms": ["google", "reddit", "youtube"],
  "tasks": [
    {"id": "t1", "source": "reddit", "query": "portable ice maker recommendations 2024", "language": "en", "max_results": 10},
    {"id": "t2", "source": "reddit", "query": "ice maker problems loud slow production complaints", "language": "en", "max_results": 10},
    {"id": "t3", "source": "google", "query": "best portable ice maker honest review 2024", "language": "en", "max_results": 10},
    {"id": "t4", "source": "google", "query": "portable ice maker complaints defects malfunction", "language": "en", "max_results": 10},
    {"id": "t5", "source": "google", "query": "site:amazon.com ice maker review negative problems", "language": "en", "max_results": 10},
    {"id": "t6", "source": "youtube", "query": "portable ice maker honest review 2024", "language": "en", "max_results": 10},
    {"id": "t7", "source": "google", "query": "GE Opal vs Frigidaire ice maker comparison review", "language": "en", "max_results": 10},
    {"id": "t8", "source": "google", "query": "countertop ice maker noise energy consumption complaints", "language": "en", "max_results": 10}
  ],
  "estimated_total": 30
}
```

### 예시 B: 독일 시장 · Geschirrspüler (식기세척기, 전자제품)
— 비영어권 Reddit 선택적 허용(r/de) 적용 예시
```json
{
  "market": "독일",
  "product_category": "Geschirrspüler",
  "target_demographic": "가정용 주방가전 구매자",
  "keywords": ["Geschirrspüler", "Test", "Erfahrung", "Bewertung", "Probleme", "Nachteile", "Meinung"],
  "filter_keywords": ["Geschirrspüler", "Spülmaschine", "Test", "Erfahrung", "Erfahrungsbericht", "Bewertung", "Probleme", "Nachteile", "kaputt", "Reparatur", "Lärm", "Wasserverbrauch", "empfehlenswert", "Vergleich"],
  "languages": ["de"],
  "platforms": ["google", "youtube"],
  "tasks": [
    {"id": "t1", "source": "google", "query": "Geschirrspüler Test Erfahrung 2024 Empfehlung", "language": "de", "max_results": 10},
    {"id": "t2", "source": "google", "query": "Geschirrspüler Probleme häufige Fehler Kundenberichte", "language": "de", "max_results": 10},
    {"id": "t3", "source": "google", "query": "site:computerbase.de Geschirrspüler Test Erfahrung", "language": "de", "max_results": 10},
    {"id": "t4", "source": "google", "query": "site:idealo.de Geschirrspüler Bewertungen Nachteile", "language": "de", "max_results": 10},
    {"id": "t5", "source": "google", "query": "site:amazon.de Geschirrspüler Bewertungen Probleme", "language": "de", "max_results": 10},
    {"id": "t6", "source": "google", "query": "Bosch Siemens Miele Geschirrspüler Vergleich Unterschied", "language": "de", "max_results": 10},
    {"id": "t7", "source": "google", "query": "site:reddit.com/r/de Geschirrspüler Erfahrung empfehlen", "language": "de", "max_results": 10},
    {"id": "t8", "source": "youtube", "query": "Geschirrspüler Test Empfehlung 2024", "language": "de", "max_results": 10}
  ],
  "estimated_total": 30
}
```

### 예시 C: 한국 시장 · 비타민C 세럼 (화장품)
— 비영어권 Reddit **금지** + 뷰티 카테고리 예시 (현지 플랫폼 우선)
```json
{
  "market": "한국",
  "product_category": "비타민C 세럼",
  "target_demographic": "20~30대 스킨케어 소비자, 민감성/지성 피부",
  "keywords": ["비타민C 세럼", "후기", "리뷰", "추천", "부작용", "단점", "트러블"],
  "filter_keywords": ["비타민C 세럼", "비타민씨 세럼", "세럼", "앰플", "후기", "리뷰", "발림성", "지속력", "부작용", "트러블", "피부타입", "민감성", "지성", "성분"],
  "languages": ["ko"],
  "platforms": ["google", "youtube"],
  "tasks": [
    {"id": "t1", "source": "google", "query": "site:hwahae.co.kr 비타민C 세럼 리뷰 성분", "language": "ko", "max_results": 10},
    {"id": "t2", "source": "google", "query": "site:oliveyoung.co.kr 비타민C 세럼 후기 리뷰", "language": "ko", "max_results": 10},
    {"id": "t3", "source": "google", "query": "비타민C 세럼 부작용 트러블 단점", "language": "ko", "max_results": 10},
    {"id": "t4", "source": "google", "query": "비타민C 세럼 민감성 피부 자극 불만", "language": "ko", "max_results": 10},
    {"id": "t5", "source": "google", "query": "비타민C 세럼 추천 솔직후기 2024", "language": "ko", "max_results": 10},
    {"id": "t6", "source": "google", "query": "site:blog.naver.com 비타민C 세럼 6개월 사용기", "language": "ko", "max_results": 10},
    {"id": "t7", "source": "google", "query": "클렌스포어 vs 클리니크 비타민C 세럼 비교", "language": "ko", "max_results": 10},
    {"id": "t8", "source": "youtube", "query": "비타민C 세럼 발림성 지속력 내돈내산", "language": "ko", "max_results": 10}
  ],
  "estimated_total": 30
}
```
**주의**: 예시 C에는 `reddit` source가 전혀 없음. 한국 시장은 reddit 금지이므로 현지 플랫폼(화해, 올리브영, 네이버 블로그)을 `site:` 쿼리로 활용.
"""


class Planner:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)
        from config import GEMINI_MODEL
        self.model = GEMINI_MODEL

    async def create(self, user_request: str) -> ResearchPlan:
        """사용자 자연어 요청 → ResearchPlan JSON (하네스 엔지니어링 v2)"""

        # 1. 시장·제품 유형 자동 감지
        detected_type = detect_product_type(user_request)
        market_hint = get_market_context(user_request, product_type=detected_type)
        type_label = _PRODUCT_TYPE_LABELS.get(detected_type, "일반")
        type_specific_block = _build_product_type_block(detected_type)

        # 2. 시장 이름 역조회 (Reddit 가이드용)
        detected_market = _resolve_market_name(user_request)
        reddit_guidance = _get_reddit_guidance(detected_market)

        # 3. 프롬프트 조립
        prompt = f"""당신은 글로벌 시장 VOC(Voice of Customer) 조사 전문가입니다.
사용자 요청을 분석하여 **해당 시장의 언어와 플랫폼에 최적화된** 조사계획 JSON을 작성하세요.

사용자 요청: "{user_request}"
자동 감지: 제품 유형 = **{type_label}**
{f'**시장 정보 (자동 감지됨 — 반드시 이 설정을 따르세요):**' + chr(10) + market_hint if market_hint else ''}
{type_specific_block}

---

## ■ STEP 1: 시장 & 플랫폼 파악

아래 규칙을 JSON 생성 전에 내부적으로 확인하세요:
- 해당 시장의 **주요 언어**로만 모든 쿼리 작성
- 특정 사이트를 검색하려면 source="google" + query에 site: 연산자 사용

### 사용 가능한 source 값 (검색엔진 + 플랫폼)

**기본 플랫폼**
- `"google"` : 일반 웹 검색 (전 시장 공통)
- `"youtube"` : YouTube 영상/댓글 (전 시장 공통)
- `"reddit"` : 영어권 커뮤니티 (**아래 Reddit 규칙 참고, 비영어권 금지**)

**로컬 검색엔진 (해당 시장에서만 사용)**
- `"naver"` : 한국 시장 필수 — Naver 블로그·카페 = 생생한 한국어 VOC
- `"yahoo_jp"` : 일본 시장 권장 — Yahoo Japan 점유율 약 25%
- `"yandex"` : 러시아·CIS·동유럽 시장 — Yandex 점유율 약 60%
- `"baidu"` : 중국 시장 필수 — Baidu 점유율 약 70%, google.cn은 차단됨

**제품 리뷰 특화 엔진 (카테고리에 따라 추가)**
- `"ebay"` : eBay 제품 리뷰 — 미국·영국·독일·이탈리아·프랑스 시장
- `"walmart"` : Walmart 제품 리뷰 — 미국 전용
- `"home_depot"` : 가정용품·공구 리뷰 — 미국 전용
- `"google_shopping"` : 쇼핑 비교 검색 — 전 시장 (gl 자동 적용)
- `"amazon"` : Amazon 제품 리뷰 — 미국·일본·독일·영국 등 전 시장

### 엔진 선정 가이드 (시장+카테고리 조합)
| 상황 | 추가 source |
|------|------------|
| 한국 시장 | `naver` 필수 추가 (google과 병행) |
| 일본 시장 | `yahoo_jp` 권장 + `amazon` (아마존재팬) |
| 러시아/동유럽 시장 | `yandex` 필수 + google 보조 |
| 중국 시장 | `baidu` 전용 (google 사용 불가) |
| 미국 가전/전자제품 VOC | `amazon` + `ebay` + `walmart` |
| 미국 가정용품/공구 | `home_depot` + `walmart` |
| EU 가전/전자제품 VOC | `ebay` + `amazon` |
| 글로벌 쇼핑/제품 비교 | `google_shopping` |

### Reddit 사용 규칙 (시장별 차등 적용):
{reddit_guidance}

---

## ■ STEP 2: 태스크 분배 계획 (총 8개 고정)

반드시 아래 감성/관점 분배를 준수하세요:
| 유형        | 최소 개수 | 쿼리 키워드 예시                                  |
|------------|---------|------------------------------------------------|
| 부정/불만   | 3개      | 불만, 단점, 결함, 고장, 클레임, complaints, Probleme |
| 긍정/추천   | 2개      | 추천, 만족, 후기, review, empfehlen, recommande  |
| 비교/평가   | 2개      | vs, 비교, Vergleich, comparatif, comparison     |
| 기능/특성   | 1개      | 소음, 에너지, 설치, noise, Lärm, installazione  |

**각 쿼리에는 반드시 제품명/핵심 카테고리명을 포함하세요.**

---

## ■ STEP 3: JSON 스키마 (다른 텍스트 없이 JSON만 출력)

{{
  "market": "조사 대상 시장/국가",
  "product_category": "제품 카테고리 (사용자 요청에서 정확히 추출)",
  "target_demographic": "타겟 소비자층",
  "keywords": ["검색 쿼리용 핵심 키워드 5~8개 (해당 시장 언어)"],
  "filter_keywords": [
    "제품명 현지어 표기 (지역 변형어 포함)",
    "제품 특화 불만/결함 표현 (현지어)",
    "제품 주요 기능 키워드 (현지어)",
    "리뷰/추천/비추 표현 (현지어)",
    "총 12~15개 — 반드시 모두 해당 시장 언어로, 한국어 절대 포함 금지"
  ],
  "languages": ["해당 시장의 주요 언어 코드"],
  "platforms": ["해당 시장 최적화 플랫폼 목록"],
  "tasks": [
    {{
      "id": "t1",
      "source": "google 또는 reddit 또는 youtube",
      "query": "실제 검색 쿼리 (해당 시장 언어, 제품명 포함)",
      "language": "언어 코드",
      "max_results": 10
    }}
  ],
  "estimated_total": 30
}}

---

## ■ 출력 전 규칙 체크리스트 (반드시 확인)

[ ] 모든 쿼리가 해당 시장 언어로 작성됨 (영어 시장=영어, 독일=독일어, 프랑스=프랑스어)
[ ] source가 "google"/"reddit"/"youtube" 중 하나 (도메인명 절대 금지: amazon.de, idealo.de 등)
[ ] Reddit 허용 규칙 준수: {reddit_guidance.split(chr(10))[0]}
[ ] 각 쿼리에 제품명/카테고리명 포함 (너무 광범위한 쿼리 없음)
[ ] 정확히 8개 tasks 생성
[ ] 부정 쿼리 3개 이상, 긍정 2개 이상, 비교 2개 이상
[ ] target_demographic 값을 쿼리에 절대 포함하지 않음 (Z세대, Millennials 등 쿼리 삽입 금지)
[ ] 타 언어 단어 혼입 금지 (독일어 쿼리에 한국어·중국어 단어 없음)

---

{_FEW_SHOT_EXAMPLES}"""

        # 4. Gemini 호출 — 지수 백오프 재시도
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    },
                )
                break
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                is_overload = any(
                    code in err_str for code in ("503", "500", "overloaded", "UNAVAILABLE")
                )
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Planner.create %s — attempt %d/%d, retry in %.1fs. Error: %s",
                        "overload" if is_overload else "failed",
                        attempt, _MAX_RETRIES, delay, err_str[:120],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Planner.create permanently failed after %d attempts. Last error: %s",
                        _MAX_RETRIES, err_str[:200],
                    )
                    raise
        else:
            raise last_exc  # type: ignore[misc]

        raw = response.text.strip()
        data = json.loads(raw)

        # 5. 후처리 검증 & 수정
        data = self._validate_and_fix_plan(data, detected_market)

        # 6. filter_keywords → plan.keywords 통합
        ai_filter_kws: list[str] = data.pop("filter_keywords", [])

        # tasks에 ID 보장 + 상태 필드 초기화
        for i, task in enumerate(data.get("tasks", [])):
            if not task.get("id"):
                task["id"] = f"task_{uuid.uuid4().hex[:6]}"
            task["completed"] = False
            task["results_count"] = 0

        plan = ResearchPlan(**data)

        # AI filter_keywords를 plan.keywords에 병합 (중복 제거)
        if ai_filter_kws:
            existing_lower = {k.lower() for k in plan.keywords}
            for kw in ai_filter_kws:
                kw = kw.strip()
                if kw and kw.lower() not in existing_lower:
                    plan.keywords.append(kw)
                    existing_lower.add(kw.lower())
        else:
            # AI 생성 실패 시 하드코딩 fallback
            market_cfg = resolve_market(plan.market)
            if market_cfg:
                fallback_kws = get_native_keywords(
                    market_cfg, product_name=plan.product_category
                )
                existing_lower = {k.lower() for k in plan.keywords}
                for kw in fallback_kws:
                    if kw.lower() not in existing_lower:
                        plan.keywords.append(kw)
                        existing_lower.add(kw.lower())

        return plan

    @staticmethod
    def _normalize_task(
        task: dict,
        reddit_allowed: bool,
        valid_sources: set[str],
        corrections: dict | None = None,
    ) -> dict | None:
        """단일 태스크 dict의 source/query 정규화 (create/revise 공용).

        반환:
          - 정규화된 task dict (in-place 수정 후 반환)
          - 빈 쿼리인 경우 None (호출자가 skip 처리)

        교정 동작:
          1. source에 도메인명이 들어간 경우 → google + site: 쿼리로 변환
          2. Reddit 비허용 시장에서 reddit source → google으로 변환
          3. 빈 쿼리 → None 반환

        corrections dict가 주어지면 적용 횟수를 카운트한다 (관찰성).
        """
        src = str(task.get("source", "google")).lower().strip()
        query = str(task.get("query", "")).strip()

        if not query:
            if corrections is not None:
                corrections["empty_removed"] = corrections.get("empty_removed", 0) + 1
            return None

        if src not in valid_sources:
            task["query"] = f"site:{src} {query}"
            task["source"] = "google"
            src = "google"
            if corrections is not None:
                corrections["domain_to_site"] = corrections.get("domain_to_site", 0) + 1

        if src == "reddit" and not reddit_allowed:
            task["source"] = "google"
            if corrections is not None:
                corrections["reddit_to_google"] = corrections.get("reddit_to_google", 0) + 1

        return task

    def _validate_and_fix_plan(self, data: dict, market: str) -> dict:
        """생성된 계획의 품질 검증 및 자동 수정.

        수정 항목 (실제 수정 — _normalize_task 위임):
          1. source에 도메인명이 들어간 경우 → google + site: 쿼리로 변환
          2. Reddit 비허용 시장에서 reddit source 사용 → google + site: 로 변환
          3. 빈 쿼리 제거
          4. 태스크 수 상한 클리핑 (최대 12개)

        관찰성 항목 (경고 로그만 기록, 자동 수정 X):
          5. 태스크 수 하한 (6개 미만) 감지 → WARNING
          6. 감성 분배 불균형 (부정<3 or 긍정<2 or 비교<2) → WARNING
        """
        reddit_cfg = _REDDIT_COMMUNITIES.get(market, {"allowed": False})
        reddit_allowed = reddit_cfg.get("allowed", False)

        valid_sources = {"google", "reddit", "youtube"}
        fixed_tasks: list[dict] = []
        corrections = {"domain_to_site": 0, "reddit_to_google": 0, "empty_removed": 0}

        for task in data.get("tasks", []):
            normalized = self._normalize_task(
                task, reddit_allowed, valid_sources, corrections
            )
            if normalized is not None:
                fixed_tasks.append(normalized)

        # ── 태스크 수 상한 클리핑 ─────────────────────────────────────────
        if len(fixed_tasks) > 12:
            logger.warning(
                "Plan task count %d exceeds cap 12 — truncating", len(fixed_tasks)
            )
            fixed_tasks = fixed_tasks[:12]

        # ── 태스크 수 하한 관찰 ──────────────────────────────────────────
        if len(fixed_tasks) < 6:
            logger.warning(
                "Plan task count %d is below recommended minimum (6). "
                "Market=%r, corrections=%s",
                len(fixed_tasks), market, corrections,
            )

        # ── 감성 분배 검증 (관찰성) ──────────────────────────────────────
        sentiment_counts = {"negative": 0, "positive": 0, "comparison": 0, "feature": 0}
        for task in fixed_tasks:
            buckets = _classify_query_sentiment(task.get("query", ""))
            for b in buckets:
                if b in sentiment_counts:
                    sentiment_counts[b] += 1

        expected = {"negative": 3, "positive": 2, "comparison": 2}
        shortfalls = [
            f"{k}: {sentiment_counts[k]}/{v}"
            for k, v in expected.items()
            if sentiment_counts[k] < v
        ]
        if shortfalls:
            logger.warning(
                "Plan sentiment distribution shortfall — %s "
                "(full counts: %s, market=%r)",
                ", ".join(shortfalls), sentiment_counts, market,
            )

        # 교정 사항 요약 로그
        if any(v > 0 for v in corrections.values()):
            logger.info(
                "Plan corrections applied: %s (market=%r)", corrections, market
            )

        data["tasks"] = fixed_tasks
        return data

    async def revise(
        self, ctx: AgentContext, gaps: list[str]
    ) -> PlanRevision:
        """부족분 기반 조사계획 수정"""

        current_plan = ctx.plan
        collected_summary = (
            f"수집 {len(ctx.collected_items)}건, "
            f"긍정 {ctx.sentiment_dist.get('positive', 0)}, "
            f"부정 {ctx.sentiment_dist.get('negative', 0)}, "
            f"중립 {ctx.sentiment_dist.get('neutral', 0)}"
        )

        # 시장별 Reddit 가이드 생성
        reddit_guidance = _get_reddit_guidance(current_plan.market)

        prompt = f"""현재 VOC 조사의 부족분을 보완할 추가 검색 태스크를 생성하세요.

현재 상황:
- 시장: {current_plan.market}
- 제품: {current_plan.product_category}
- {collected_summary}
- 부족분: {', '.join(gaps)}

기존 검색 쿼리: {[t.query for t in current_plan.tasks]}

## Reddit 사용 규칙:
{reddit_guidance}

추가할 검색 태스크를 JSON 배열로 응답하세요 (다른 텍스트 없이 JSON만):
[
  {{
    "id": "고유ID",
    "source": "google 또는 reddit(허용 시장만) 또는 youtube",
    "query": "해당 시장 언어로 된 검색 쿼리 (제품명 반드시 포함)",
    "language": "해당 시장 언어 코드",
    "max_results": 10
  }}
]

규칙:
- 기존 쿼리와 겹치지 않는 새로운 쿼리
- 부족분을 직접 해소할 수 있는 쿼리
- 2~4개 정도
- 모든 쿼리에 제품명/서비스명 반드시 포함
- 검색 쿼리는 반드시 해당 시장의 언어로 작성
- source에 도메인명 사용 금지 (amazon.de, idealo.de 등) → google + site: 쿼리 사용
- Reddit 허용 규칙: {reddit_guidance.split(chr(10))[0]}
- 너무 광범위한 쿼리 사용 금지"""

        # Gemini 호출 — 지수 백오프 재시도
        last_exc_r: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    },
                )
                break
            except Exception as exc:
                last_exc_r = exc
                err_str = str(exc)
                is_overload = any(
                    code in err_str for code in ("503", "500", "overloaded", "UNAVAILABLE")
                )
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Planner.revise %s — attempt %d/%d, retry in %.1fs. Error: %s",
                        "overload" if is_overload else "failed",
                        attempt, _MAX_RETRIES, delay, err_str[:120],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Planner.revise permanently failed after %d attempts. Last error: %s",
                        _MAX_RETRIES, err_str[:200],
                    )
                    raise
        else:
            raise last_exc_r  # type: ignore[misc]

        raw = response.text.strip()
        new_tasks_data = json.loads(raw)

        # 배열로 래핑된 경우와 단일 객체인 경우 모두 처리
        if isinstance(new_tasks_data, dict):
            new_tasks_data = [new_tasks_data]

        # revise 결과도 검증 (_normalize_task 공용 헬퍼 사용 — create와 동일 로직)
        market = current_plan.market
        reddit_cfg = _REDDIT_COMMUNITIES.get(market, {"allowed": False})
        reddit_allowed = reddit_cfg.get("allowed", False)
        valid_sources = {"google", "reddit", "youtube"}
        revise_corrections = {"domain_to_site": 0, "reddit_to_google": 0, "empty_removed": 0}

        new_tasks = []
        for t in new_tasks_data:
            normalized = self._normalize_task(
                t, reddit_allowed, valid_sources, revise_corrections
            )
            if normalized is None:
                continue
            if not normalized.get("id"):
                normalized["id"] = f"task_{uuid.uuid4().hex[:6]}"
            normalized["completed"] = False
            normalized["results_count"] = 0
            new_tasks.append(SearchTask(**normalized))

        # 교정 사항 요약 로그 (revise도 create와 동일하게 관찰성 확보)
        if any(v > 0 for v in revise_corrections.values()):
            logger.info(
                "Revise corrections applied: %s (market=%r)", revise_corrections, market
            )

        # 기존 계획에 태스크 추가
        ctx.plan.tasks.extend(new_tasks)

        # 재계획 후에도 네이티브 키워드 유지
        market_cfg = resolve_market(ctx.plan.market)
        if market_cfg and not ctx.plan.keywords:
            ctx.plan.keywords = get_native_keywords(
                market_cfg, product_name=ctx.plan.product_category
            )

        return PlanRevision(
            iteration=ctx.iteration,
            reason=", ".join(gaps),
            added_tasks=new_tasks,
        )


# ─── 유틸 ────────────────────────────────────────────────────────────────────

def _resolve_market_name(user_request: str) -> str:
    """사용자 요청 텍스트에서 MARKET_CONFIG 키(시장명)를 역조회.

    resolve_market()이 config dict를 반환하므로, MARKET_CONFIG를 역순 탐색해
    동일 country code를 가진 키를 찾는다.
    예: "독일 식기세척기 구매 전 소비자 의견" → "독일"

    감지 실패 시:
      - 빈 문자열 반환 → 호출자가 _get_reddit_guidance("")로 "reddit 금지" 폴백
      - 경고 로그 기록 (silent fallback 관찰성 확보)
    """
    config = resolve_market(user_request)
    if config is None:
        logger.warning(
            "Market detection failed for request: %r — falling back to reddit-disabled mode",
            user_request[:120],
        )
        return ""
    target_code = config.get("code", "")
    for market_name, market_cfg in MARKET_CONFIG.items():
        if market_cfg.get("code") == target_code:
            return market_name
    logger.warning(
        "Market code %r resolved but not found in MARKET_CONFIG keys", target_code
    )
    return ""
