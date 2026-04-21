"""최종 구조화 — 감성 분류 확정 + 토픽 태깅 + 번역"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from google import genai

from agent.state import AgentContext
from models.schemas import VocItem

logger = logging.getLogger(__name__)

# 배치 간 대기 시간 (초) — rate limit 초과 방지
_BATCH_DELAY = 1.0

# 503/500 발생 시 재시도 설정
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0   # 첫 재시도 대기 (초), 이후 지수 증가


class Synthesizer:
    """수집된 VOC를 최종 분석/구조화"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)
        from config import GEMINI_MODEL
        self.model = GEMINI_MODEL

    async def run(self, ctx: AgentContext) -> dict:
        """전체 VOC에 대해 감성 확정 + 토픽 태깅 + 한국어 번역"""

        items = ctx.collected_items
        if not items:
            return {"items": [], "summary": {}}

        # 배치로 처리 (5건씩)
        batch_size = 5
        total_batches = (len(items) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(items), batch_size)):
            batch = items[i : i + batch_size]
            logger.debug(
                "Synthesizer batch %d/%d (items %d~%d)",
                batch_idx + 1, total_batches, i + 1, min(i + batch_size, len(items)),
            )
            await self._enrich_batch(batch, ctx)

            # RC-A: 배치 간 딜레이 — rate limit 초과 방지
            # 마지막 배치 이후에는 대기 불필요
            if i + batch_size < len(items):
                await asyncio.sleep(_BATCH_DELAY)

        summary = {
            "total": len(items),
            "verified": ctx.verified_count,
            "duplicates_removed": ctx.dedup_count,
            "sentiment": ctx.sentiment_dist,
            "iterations": ctx.iteration,
            "platforms": list({item.platform for item in items}),
        }

        return {"items": [item.model_dump(mode="json") for item in items], "summary": summary}

    async def _enrich_batch(self, batch: list[VocItem], ctx: AgentContext):
        """배치 단위로 관련성 판별 + 감성/토픽/번역 보강

        RC-B: asyncio.to_thread — 이벤트 루프 블로킹 방지
        RC-C: 503/500 재시도 + 오류 로깅
        """

        product = ctx.plan.product_category if ctx.plan else ""
        market = ctx.plan.market if ctx.plan else ""

        texts = []
        for item in batch:
            texts.append({
                "id": item.id,
                "text": item.original_text[:500],
                "current_sentiment": item.sentiment,
            })

        prompt = f"""다음 VOC(소비자 의견) 목록을 분석하세요.
조사 대상 제품: {product}
조사 대상 시장: {market}

각 VOC에 대해 **반드시 모든 항목을 판별**하세요:
1. **관련성 판별 (relevant: true/false)** — 이 의견이 "{product}"에 직접 관련되는가?
   - true: 해당 제품/서비스를 직접 언급하거나 사용 경험을 말하는 의견
   - false: 다른 제품, 일반적인 이야기, 광고, 제품과 무관한 내용
2. 감성 판별 (positive/negative/neutral)
3. 토픽 태그 (한국어, 2~4개)
4. 한국어 번역 (자연스러운 번역)

JSON 배열로 응답 (다른 텍스트 없이):
[
  {{
    "id": "원본 ID",
    "relevant": true,
    "sentiment": "positive/negative/neutral",
    "topics": ["토픽1", "토픽2"],
    "translated_text": "한국어 번역"
  }}
]

VOC 목록:
{json.dumps(texts, ensure_ascii=False)}"""

        # RC-B + RC-C: asyncio.to_thread + 지수 백오프 재시도
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                # RC-B: to_thread로 동기 SDK 호출을 이벤트 루프 밖에서 실행
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    },
                )

                results = json.loads(response.text.strip())

                # 결과를 원본에 반영
                result_map = {r["id"]: r for r in results}
                for item in batch:
                    if item.id in result_map:
                        r = result_map[item.id]
                        item.sentiment = r.get("sentiment", item.sentiment)
                        item.topics = r.get("topics", item.topics)
                        item.translated_text = r.get("translated_text", item.translated_text)
                        # 관련성 판별 결과를 approved에 명시 반영
                        if r.get("relevant", True):
                            item.approved = True
                        else:
                            item.approved = False

                return  # 성공 시 즉시 반환

            except Exception as exc:
                last_exc = exc
                err_str = str(exc)

                # RC-C: 503/500(수요 급증) 여부 구별해서 로깅
                is_overload = any(
                    code in err_str for code in ("503", "500", "overloaded", "UNAVAILABLE")
                )

                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))  # 2s → 4s → 8s
                    if is_overload:
                        logger.warning(
                            "Synthesizer batch overload (503/500) — attempt %d/%d, "
                            "retry in %.1fs. Error: %s",
                            attempt, _MAX_RETRIES, delay, err_str[:120],
                        )
                    else:
                        logger.warning(
                            "Synthesizer batch failed — attempt %d/%d, "
                            "retry in %.1fs. Error: %s",
                            attempt, _MAX_RETRIES, delay, err_str[:120],
                        )
                    await asyncio.sleep(delay)
                else:
                    # 최종 실패: 조용히 넘어가되 반드시 로그 기록
                    logger.error(
                        "Synthesizer batch permanently failed after %d attempts "
                        "(items: %s). Keeping original values. Last error: %s",
                        _MAX_RETRIES,
                        [item.id[:8] for item in batch],
                        err_str[:200],
                    )
                    # 기존 값 유지 (원본 sentiment/topics 보존)
