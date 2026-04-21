"""SerpApi fixture 캡처 — 일회성 실행. 3 credits 소진.

실행 방법:
    cd voc-collector-serp/backend
    SERPAPI_KEY=<key> venv/Scripts/python.exe ../scripts/capture_fixtures.py

캡처 후 account.json으로 잔여 credits를 자동 출력합니다.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from serpapi import GoogleSearch  # type: ignore[import]
except ImportError:
    print("ERROR: serpapi not installed. Run: pip install google-search-results==2.4.2")
    sys.exit(1)

API_KEY = os.environ.get("SERPAPI_KEY", "")
if not API_KEY:
    API_KEY = input("SERPAPI_KEY: ").strip()

if not API_KEY:
    print("ERROR: SERPAPI_KEY is required")
    sys.exit(1)

FIXTURE_DIR = Path(__file__).parent.parent / "backend" / "tests" / "fixtures" / "serpapi"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

CAPTURES = [
    {
        "name": "us_ice_maker_organic",
        "params": {
            "q": "portable ice maker review complaints",
            "gl": "us",
            "hl": "en",
            "num": 10,
        },
    },
    {
        "name": "de_eismaschine_organic",
        "params": {
            "q": "Eismaschine Test Erfahrungen",
            "gl": "de",
            "hl": "de",
            "lr": "lang_de",
            "num": 10,
        },
    },
    {
        "name": "it_macchina_ghiaccio_organic",
        "params": {
            "q": "macchina del ghiaccio portatile opinioni",
            "gl": "it",
            "hl": "it",
            "num": 10,
        },
    },
]


def check_credits() -> int:
    url = f"https://serpapi.com/account.json?api_key={API_KEY}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.load(r)
    return int(data.get("total_searches_left", 0))


def main() -> None:
    print("=== SerpApi Fixture Capture ===")
    before = check_credits()
    print(f"Credits before: {before}\n")

    if before < len(CAPTURES):
        print(f"ERROR: Not enough credits ({before} < {len(CAPTURES)})")
        sys.exit(1)

    for cap in CAPTURES:
        out_path = FIXTURE_DIR / f"{cap['name']}.json"

        # 이미 캡처된 경우 skip
        if out_path.exists():
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if existing.get("organic_results"):
                print(f"SKIP {cap['name']} (already exists, {len(existing['organic_results'])} results)")
                continue

        print(f"Capturing {cap['name']}...")
        params = {
            **cap["params"],
            "engine": "google",
            "api_key": API_KEY,
            "no_cache": "false",
        }
        try:
            data = GoogleSearch(params).get_dict()
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        if "error" in data:
            print(f"  API ERROR: {data['error']}")
            continue

        organic_count = len(data.get("organic_results", []))
        print(f"  → {out_path.name}: {organic_count} organic results")

        if organic_count == 0:
            print("  WARNING: No organic results - check query or credits")

        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    after = check_credits()
    print(f"\nCredits after: {after} (consumed: {before - after})")
    print("\nFixture files:")
    for f in sorted(FIXTURE_DIR.glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:50s} {size_kb:6.1f} KB")


if __name__ == "__main__":
    main()
