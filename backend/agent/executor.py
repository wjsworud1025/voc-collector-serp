"""소스별 수집 실행기"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from agent.state import AgentContext
from collectors.base import BaseCollector
from collectors.reddit import RedditCollector
from collectors.serpapi_engine_configs import ENGINES_NO_GEO, SERPAPI_ENGINES
from collectors.serpapi_search import SerpApiSearchCollector
from collectors.web_reader import WebReader
from collectors.youtube import YouTubeCollector
from market_config import resolve_market
from models.schemas import AgentEvent, SearchTask, VocItem
from verifier import Verifier


class Executor:
    """조사계획의 각 태스크를 소스에 맞는 수집기로 실행"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.web_reader = WebReader()
        self.verifier = Verifier()
        self._collectors: dict[str, BaseCollector] = {
            "google": SerpApiSearchCollector(),  # SerpApi.com으로 교체
            "reddit": RedditCollector(),
            "youtube": YouTubeCollector(),
        }

    async def run(
        self, task: SearchTask, ctx: AgentContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """단일 태스크 실행"""

        yield AgentEvent(
            type="task_started",
            message=f"{task.source} 검색: {task.query}",
            data={"source": task.source, "query": task.query},
        )

        collector = self._collectors.get(task.source)
        engine = "google"  # SerpApiSearchCollector에 전달할 실제 엔진명

        # SerpApi 멀티엔진: task.source가 알려진 엔진명이면 SerpApiSearchCollector 재사용
        if not collector and task.source in SERPAPI_ENGINES:
            collector = self._collectors["google"]
            engine = task.source

        # 도메인명(예: amazon.de, idealo.de)이 source로 온 경우 → google site: 검색으로 변환
        elif not collector and "." in task.source:
            site_prefix = f"site:{task.source} "
            if not task.query.startswith(site_prefix):
                task.query = site_prefix + task.query
            collector = self._collectors["google"]

        elif collector and task.source == "google":
            engine = "google"  # 명시적 설정 (기본값이지만 가독성 위해)

        if not collector:
            yield AgentEvent(
                type="task_skipped",
                message=f"지원하지 않는 소스: {task.source}",
            )
            task.completed = True
            return

        try:
            # plan keywords + 제품 카테고리 → 사전 필터링용
            filter_keywords = list(ctx.plan.keywords) if ctx.plan.keywords else []
            if ctx.plan.product_category and ctx.plan.product_category not in filter_keywords:
                filter_keywords.insert(0, ctx.plan.product_category)

            # SerpApi 지역·언어 파라미터
            # ENGINES_NO_GEO(naver, yahoo_jp, yandex, baidu, walmart, home_depot)는 제외
            # google_shopping, ebay, amazon은 gl만 사용 (lr/hl 불필요)
            search_geo: dict = {}
            if task.source not in {"reddit", "youtube"} and engine not in ENGINES_NO_GEO:
                market_info = resolve_market(ctx.plan.market)
                if market_info:
                    gl = market_info["code"].lower()
                    search_geo["gl"] = gl
                    # Google 계열만 lr/hl 추가
                    if engine in {"google", "google_shopping"}:
                        search_geo["lr"] = f"lang_{market_info['language']}"
                        search_geo["hl"] = market_info["language"]

            collect_kwargs: dict = {
                "query": task.query,
                "context": f"{ctx.plan.market} {ctx.plan.product_category}",
                "max_results": task.max_results,
                "keywords": filter_keywords,
            }
            # SerpApiSearchCollector에만 engine 파라미터 전달
            if task.source not in {"reddit", "youtube"}:
                collect_kwargs["engine"] = engine
                collect_kwargs.update(search_geo)

            items = await collector.collect(**collect_kwargs)

            # L1~L4 검증 — 동시 실행 (최대 5개씩)
            if items:
                sem = asyncio.Semaphore(5)
                async def _verify(item: VocItem) -> VocItem:
                    async with sem:
                        return (await self.verifier.verify_batch([item]))[0]
                items = list(await asyncio.gather(*[_verify(i) for i in items]))

            added = 0
            for item in items:
                item.project_id = self.project_id
                item.compute_hash()

                if ctx.add_item(item):
                    added += 1
                    yield AgentEvent(
                        type="item_found",
                        message=f"VOC 수집: {item.original_text[:50]}...",
                        data={
                            "platform": item.platform,
                            "sentiment": item.sentiment,
                            "confidence": item.confidence,
                            "source_url": item.source_url,
                        },
                    )

            task.completed = True
            task.results_count = added

            yield AgentEvent(
                type="task_done",
                message=f"{task.source} 완료: {added}건 수집",
                data={
                    "source": task.source,
                    "query": task.query,
                    "collected": added,
                    "duplicates": len(items) - added,
                },
            )

        except Exception as e:
            yield AgentEvent(
                type="task_error",
                message=f"{task.source} 오류: {str(e)}",
                data={"source": task.source, "error": str(e)},
            )
            task.completed = True
